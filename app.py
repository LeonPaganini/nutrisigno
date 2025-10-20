# ... imports no topo:
import io
from modules import openai_utils
try:
    from modules import dashboard_utils  # se você já tiver este módulo
except Exception:
    dashboard_utils = None

# --- dentro do passo "Painel de insights" ---
st.header("6. Painel de insights")

# 1) Obter insights (com fallback hard)
try:
    ai_pack = openai_utils.generate_insights(st.session_state.data)
    insights = ai_pack.get("insights", {})
    ai_summary = ai_pack.get("ai_summary", "Resumo indisponível (modo simulado).")
except Exception as e:
    st.warning(f"Modo fallback automático: {e}")
    # fallback mínimo (se openai_utils tiver sido quebrado por algum motivo)
    peso = float(st.session_state.data.get("peso") or 70)
    altura = float(st.session_state.data.get("altura") or 170)
    altura_m = altura/100
    bmi = round(peso/(altura_m**2),1)
    insights = {
        "bmi": bmi,
        "bmi_category": "Eutrofia" if 18.5 <= bmi < 25 else ("Baixo peso" if bmi < 18.5 else ("Sobrepeso" if bmi < 30 else "Obesidade")),
        "recommended_water": round(max(1.5, peso*0.035),1),
        "water_status": "OK",
        "bristol": "Padrão dentro do esperado",
        "urine": "Hidratado",
        "motivacao": int(st.session_state.data.get("motivacao") or 3),
        "estresse": int(st.session_state.data.get("estresse") or 3),
        "sign_hint": "Use seu signo como inspiração, não como prescrição.",
        "consumption": {"water_liters": float(st.session_state.data.get("consumo_agua") or 1.5),
                        "recommended_liters": round(max(1.5, peso*0.035),1)}
    }
    ai_summary = "Resumo simulado (fallback hard)."

# 2) Cards (HTML/CSS leve para visual limpo)
card_css = """
<style>
.grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:8px;}
.card {background:#fff;border:1px solid #e6e6e6;border-radius:12px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,0.04);}
.kpi {font-size:26px;font-weight:700;margin:6px 0;}
.sub {color:#6b7280;font-size:13px;margin-top:2px;}
.badge-ok{display:inline-block;padding:2px 8px;border-radius:999px;background:#e8f7ef;color:#127a46;font-size:12px}
.badge-warn{display:inline-block;padding:2px 8px;border-radius:999px;background:#fff5e6;color:#8a5200;font-size:12px}
</style>
"""
st.markdown(card_css, unsafe_allow_html=True)

st.markdown('<div class="grid">', unsafe_allow_html=True)
def badge(text, ok=True):
    cls = "badge-ok" if ok else "badge-warn"
    return f'<span class="{cls}">{text}</span>'

st.markdown(f'''
<div class="card">
  <div>IMC</div>
  <div class="kpi">{insights.get("bmi","--")}</div>
  <div class="sub">{insights.get("bmi_category","")}</div>
</div>
''', unsafe_allow_html=True)

st.markdown(f'''
<div class="card">
  <div>Hidratação</div>
  <div class="kpi">{insights["consumption"]["water_liters"]} / {insights["consumption"]["recommended_liters"]} L</div>
  <div class="sub">{badge(insights.get("water_status","OK")=="OK" and "Meta atingida" or "Abaixo do ideal", ok=insights.get("water_status","OK")=="OK")}</div>
</div>
''', unsafe_allow_html=True)

st.markdown(f'''
<div class="card">
  <div>Digestão</div>
  <div class="kpi">Bristol</div>
  <div class="sub">{insights.get("bristol","")}</div>
</div>
''', unsafe_allow_html=True)

st.markdown(f'''
<div class="card">
  <div>Urina</div>
  <div class="kpi">Cor</div>
  <div class="sub">{insights.get("urine","")}</div>
</div>
''', unsafe_allow_html=True)

st.markdown(f'''
<div class="card">
  <div>Comportamento</div>
  <div class="kpi">Motivação {insights.get("motivacao",0)}/5</div>
  <div class="sub">Estresse {insights.get("estresse",0)}/5</div>
</div>
''', unsafe_allow_html=True)

st.markdown(f'''
<div class="card">
  <div>Insight do signo</div>
  <div class="kpi">🜚</div>
  <div class="sub">{insights.get("sign_hint","")}</div>
</div>
''', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 3) Gráficos (matplotlib) – seguros no free tier
import matplotlib.pyplot as plt

col1, col2 = st.columns(2)
with col1:
    fig = plt.figure()
    plt.title("Consumo de água (L)")
    vals = [insights["consumption"]["water_liters"], insights["consumption"]["recommended_liters"]]
    plt.bar(["Consumido", "Recomendado"], vals)
    st.pyplot(fig, clear_figure=True)

with col2:
    fig2 = plt.figure()
    plt.title("IMC")
    plt.bar(["IMC"], [insights.get("bmi", 0)])
    plt.axhline(18.5, linestyle="--"); plt.axhline(25, linestyle="--")
    st.pyplot(fig2, clear_figure=True)

# 4) Resumo textual (da IA ou simulado)
with st.expander("Resumo dos insights"):
    st.write(ai_summary)

# 5) Exportações (PDF/Imagem) – usando seus utilitários se existirem, com fallback
from modules import pdf_generator
btn1, btn2, btn3 = st.columns(3)

# PDF (insights) – fallback: gerar PDF simples com reportlab direto
def build_insights_pdf_bytes(ins):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        y = 28*cm
        c.setFont("Helvetica-Bold", 14); c.drawString(2*cm, y, "NutriSigno — Painel de Insights"); y -= 1*cm
        c.setFont("Helvetica", 10)
        for k,v in [
          ("IMC", f"{ins['bmi']} ({ins['bmi_category']})"),
          ("Hidratação", f"{ins['consumption']['water_liters']} / {ins['consumption']['recommended_liters']} L"),
          ("Bristol", ins["bristol"]),
          ("Urina", ins["urine"]),
          ("Motivação/Estresse", f"{ins['motivacao']}/5 · {ins['estresse']}/5"),
          ("Insight do signo", ins["sign_hint"]),
        ]:
            c.drawString(2*cm, y, f"{k}: {v}"); y -= 0.8*cm
            if y < 2*cm: c.showPage(); y = 28*cm
        c.save()
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        return b"%PDF-1.4\n% fallback vazio"

with btn1:
    pdf_bytes = build_insights_pdf_bytes(insights)
    st.download_button("Exportar PDF", data=pdf_bytes, file_name="insights.pdf", mime="application/pdf")

# Imagem compartilhável (post)
def build_share_png_bytes(ins):
    import matplotlib.pyplot as plt
    import numpy as np
    fig = plt.figure(figsize=(6,6), dpi=200)
    plt.title("NutriSigno — Resumo", pad=12)
    text = (
        f"IMC: {ins['bmi']} ({ins['bmi_category']})\n"
        f"Hidratação: {ins['consumption']['water_liters']} / {ins['consumption']['recommended_liters']} L\n"
        f"Bristol: {ins['bristol']}\nUrina: {ins['urine']}\n"
        f"Motivação/Estresse: {ins['motivacao']}/5 · {ins['estresse']}/5\n"
        f"Signo: {ins.get('sign_hint','')}\n"
        f"#NutriSigno"
    )
    plt.axis("off")
    plt.text(0.02, 0.98, text, va="top", ha="left", wrap=True)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()

with btn2:
    img_bytes = build_share_png_bytes(insights)
    st.download_button("Baixar imagem", data=img_bytes, file_name="insights.png", mime="image/png")

with btn3:
    if st.button("Gerar plano nutricional e prosseguir para pagamento"):
        st.session_state.step += 1
        st.rerun()