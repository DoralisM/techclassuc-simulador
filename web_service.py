"""
web_service.py
--------------
Servidor web de TechClassUC.
Ruta raíz  GET /          → Panel visual HTML con reporte + gráficas.
API REST   POST /simular  → JSON con métricas Montecarlo.
           POST /analitico→ JSON con métricas M/M/c.
           POST /sensibilidad → JSON análisis de sensibilidad.
           POST /comparar → JSON comparación teoría vs simulación.
           GET  /graficas/<nombre> → imagen PNG.
"""

import os, sys, traceback
from flask import Flask, request, jsonify, send_file, render_template_string

# ── parámetros base (visibles en el panel web) ─────────────────────────────
LAM_BASE   = 10.0
MU_BASE    = 4.0
C_BASE     = 3
T_SIM      = 480.0
T_WARM     = 60.0
N_REP      = 30
SEMILLA    = 42
UNIDAD_T_SIM = "min"

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
GRAFICAS_DIR  = os.path.join(BASE_DIR, "graficas")
os.makedirs(GRAFICAS_DIR, exist_ok=True)

app = Flask(__name__)

# ── importar módulos del simulador ─────────────────────────────────────────
sys.path.insert(0, BASE_DIR)
from analitico     import calcular_mmc, comparar_con_simulacion
from montecarlo    import correr_replicas
from sensibilidad  import analisis_sensibilidad


# ── generar todo al arrancar ───────────────────────────────────────────────
class _Captura:
    def __init__(self): self.texto = ""
    def write(self, s): self.texto += s
    def flush(self): pass

_old = sys.stdout
_cap = _Captura()
sys.stdout = _cap

_mc   = correr_replicas(N=N_REP, lam=LAM_BASE, mu=MU_BASE, c=C_BASE,
                        t_sim=T_SIM, t_warm=T_WARM, semilla_base=SEMILLA)
_teo  = calcular_mmc(LAM_BASE, MU_BASE, C_BASE)
_comp = comparar_con_simulacion(LAM_BASE, MU_BASE, C_BASE, _mc["resumen"])
_sens = analisis_sensibilidad(mu=MU_BASE, N=15, semilla_base=SEMILLA)

# generar gráficas en la carpeta correcta
from visualizacion import (grafica_evolucion_temporal, grafica_histograma_wq,
                           grafica_wq_vs_c, grafica_rho_vs_lam,
                           grafica_distribucion_medias_wq, grafica_heatmap_sensibilidad)
import visualizacion as _viz
_viz.SALIDA_DIR = GRAFICAS_DIR

def generar_graficas(lam, mu, c, mc, t_sim=T_SIM, t_warm=T_WARM, sens=None):
    if sens is None:
        sens = analisis_sensibilidad(mu=mu, N=15, semilla_base=SEMILLA)

    grafica_evolucion_temporal(lam, mu, c, t_sim, SEMILLA)
    grafica_histograma_wq(mc["wq_todas"], lam, mu, c)
    grafica_wq_vs_c(lam, mu, list(range(1, 7)), N=15, t_sim=t_sim, t_warm=t_warm)
    grafica_rho_vs_lam(mu, list(range(2, 7)))
    grafica_distribucion_medias_wq(mc["replicas"], lam, mu, c)
    grafica_heatmap_sensibilidad(sens)

generar_graficas(LAM_BASE, MU_BASE, C_BASE, _mc, sens=_sens)

sys.stdout = _old
REPORTE_CONSOLA = _cap.texto


# ── plantilla HTML del panel ───────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TechClassUC — Simulador de Colas</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap" rel="stylesheet">
<style>
  :root{--bg:#0d0f14;--surface:#161a23;--border:#252a36;--accent:#00e5b0;--accent2:#5b8af5;--text:#e8eaf0;--muted:#7a8098;--warn:#f5a623;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{background:var(--bg);color:var(--text);font-family:'IBM Plex Sans',sans-serif;font-size:15px;line-height:1.6;}
  header{border-bottom:1px solid var(--border);padding:1.5rem 2.5rem;display:flex;align-items:center;gap:1rem;}
  header .logo{font-family:'IBM Plex Mono',monospace;font-size:1.1rem;color:var(--accent);font-weight:600;letter-spacing:.05em;}
  header .sub{color:var(--muted);font-size:.8rem;}
  .badge{display:inline-block;padding:2px 10px;border-radius:99px;font-size:.7rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;}
  .badge-ok{background:#0d2e24;color:var(--accent);}
  .badge-warn{background:#2e200d;color:var(--warn);}
  main{max-width:1060px;margin:0 auto;padding:2rem 2rem 4rem;}
  h2{font-family:'IBM Plex Mono',monospace;font-size:.75rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:1rem;padding-bottom:.5rem;border-bottom:1px solid var(--border);}
  .section{margin-bottom:2.5rem;}
  .metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:2rem;}
  .metric{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1rem 1.25rem;}
  .metric .label{font-size:.7rem;color:var(--muted);letter-spacing:.05em;text-transform:uppercase;margin-bottom:.4rem;}
  .metric .value{font-family:'IBM Plex Mono',monospace;font-size:1.5rem;font-weight:600;color:var(--accent);}
  .metric .ic{font-size:.7rem;color:var(--muted);margin-top:.3rem;}
  table{width:100%;border-collapse:collapse;font-size:.85rem;}
  th{text-align:left;padding:8px 12px;color:var(--muted);font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;border-bottom:1px solid var(--border);}
  td{padding:8px 12px;border-bottom:1px solid var(--border);}
  td:last-child,th:last-child{text-align:right;}
  .err-ok{color:var(--accent);}
  .err-warn{color:var(--warn);}
  .graficas{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
  .graf-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:hidden;}
  .graf-card.wide{grid-column:span 2;}
  .graf-card p{font-size:.7rem;color:var(--muted);padding:.6rem 1rem;text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid var(--border);}
  .graf-card img{width:100%;display:block;}
  pre{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1.25rem;font-family:'IBM Plex Mono',monospace;font-size:.75rem;color:var(--muted);overflow-x:auto;white-space:pre-wrap;line-height:1.7;}
  input,select{width:100%;margin-top:.35rem;padding:.55rem .65rem;border:1px solid var(--border);border-radius:6px;background:#0d0f14;color:var(--text);font-family:'IBM Plex Mono',monospace;font-size:.95rem;}
  input:focus,select:focus{outline:2px solid var(--accent2);outline-offset:1px;}
  .alert{margin:0 0 1rem 0;padding:.85rem 1rem;border-radius:8px;border:1px solid var(--border);font-size:.9rem;}
  .alert-ok{background:#0f1d18;border-color:#174f3d;color:var(--accent);}
  .alert-error{background:#2e140d;border-color:#63321f;color:#ffb08a;}
  .rho-bar-wrap{background:var(--border);border-radius:4px;height:8px;margin-top:.4rem;}
  .rho-bar{height:8px;border-radius:4px;background:var(--accent);}
  @media(max-width:640px){.graficas{grid-template-columns:1fr;}.graf-card.wide{grid-column:span 1;}.metrics{grid-template-columns:1fr 1fr;}}
</style>
</head>
<body>
<header>
  <div>
    <div class="logo">TechClassUC</div>
    <div class="sub">Simulador M/M/c &mdash; Modelos de Simulación</div>
  </div>
  <span class="badge badge-ok" style="margin-left:auto;">En línea</span>
</header>

<main>
<div class="section">
  <h2>Parámetros de simulación</h2>

  {% if estado_mensaje %}
  <div class="alert alert-{{ estado_tipo }}">{{ estado_mensaje }}</div>
  {% endif %}

  <form method="POST">

    <div class="metrics">

      <div class="metric">
        <div class="label">λ</div>
        <input type="number" step="0.1"
               name="lam"
               value="{{ lam }}">
      </div>

      <div class="metric">
        <div class="label">μ</div>
        <input type="number" step="0.1"
               name="mu"
               value="{{ mu }}">
      </div>

      <div class="metric">
        <div class="label">Técnicos (c)</div>
        <input type="number"
               name="c"
               value="{{ c }}">
      </div>

      <div class="metric">
        <div class="label">Réplicas</div>
        <input type="number"
               name="n_rep"
               value="{{ n_rep }}">
      </div>

      <div class="metric">
        <div class="label">Tiempo de ejecución</div>
        <input type="number" step="0.1"
               name="t_sim_valor"
               value="{{ t_sim_valor }}">
      </div>

      <div class="metric">
        <div class="label">Unidad</div>
        <select name="t_sim_unidad">
          <option value="min" {{ 'selected' if t_sim_unidad == 'min' else '' }}>Minutos</option>
          <option value="seg" {{ 'selected' if t_sim_unidad == 'seg' else '' }}>Segundos</option>
          <option value="horas" {{ 'selected' if t_sim_unidad == 'horas' else '' }}>Horas</option>
        </select>
      </div>

    </div>

    <button type="submit"
      style="
      padding:12px 20px;
      border:none;
      border-radius:8px;
      background:var(--accent);
      font-weight:bold;
      cursor:pointer;">
      Ejecutar simulación
    </button>

  </form>
</div>

  <!-- métricas clave -->
  <div class="section">
    <h2>Métricas clave &mdash; Montecarlo ({{ n_rep }} réplicas)</h2>
    <div class="metrics">
      <div class="metric">
        <div class="label">Wq simulado</div>
        <div class="value">{{ wq_med }} min</div>
        <div class="ic">IC 95%: [{{ wq_inf }}, {{ wq_sup }}]</div>
      </div>
      <div class="metric">
        <div class="label">Lq simulado</div>
        <div class="value">{{ lq_med }}</div>
        <div class="ic">clientes en cola</div>
      </div>
      <div class="metric">
        <div class="label">Utilización ρ</div>
        <div class="value">{{ rho_pct }}%</div>
        <div class="rho-bar-wrap"><div class="rho-bar" style="width:{{ rho_bar_pct }}%"></div></div>
      </div>
      <div class="metric">
        <div class="label">Wq analítico</div>
        <div class="value" style="color:var(--accent2)">{{ wq_teo }} min</div>
        <div class="ic">Fórmula M/M/c</div>
      </div>
      <div class="metric">
        <div class="label">Réplicas mínimas</div>
        <div class="value">{{ n_min }}</div>
        <div class="ic">para error ≤ 5%</div>
      </div>
      <div class="metric">
        <div class="label">Parámetros base</div>
        <div class="value" style="font-size:.95rem;line-height:1.8;">λ={{ lam }} &nbsp; μ={{ mu }}</div>
        <div class="ic">c={{ c }} técnicos &mdash; {{ t_sim }} min</div>
      </div>
    </div>
  </div>

  <!-- tabla validación -->
  <div class="section">
    <h2>Validación analítica M/M/c vs Simulación</h2>
    <table>
      <thead><tr><th>Métrica</th><th>Teórico</th><th>Simulado</th><th>Error relativo</th></tr></thead>
      <tbody>
        {% for f in tabla %}
        <tr>
          <td>{{ f.metrica }}</td>
          <td>{{ "%.4f"|format(f.valor_teorico) }}</td>
          <td>{{ "%.4f"|format(f.valor_simulado) }}</td>
          <td class="{{ 'err-ok' if f.error_relativo_pct < 5 else 'err-warn' }}">{{ "%.2f"|format(f.error_relativo_pct) }}%</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

    <!-- gráficas -->
  <div class="section">
    <h2>Gráficas de simulación</h2>

    <div class="graficas">
      <div class="graf-card wide">
        <p>Evolución temporal del sistema</p>
        <img src="/graficas/1_evolucion_temporal.png?v={{ graf_version }}" alt="Evolución temporal">
      </div>

      <div class="graf-card">
        <p>Histograma de tiempos de espera Wq</p>
        <img src="/graficas/2_histograma_wq.png?v={{ graf_version }}" alt="Histograma Wq">
      </div>

      <div class="graf-card">
        <p>Wq promedio vs número de técnicos c</p>
        <img src="/graficas/3_wq_vs_c.png?v={{ graf_version }}" alt="Wq vs c">
      </div>

      <div class="graf-card">
        <p>Factor de utilización ρ vs λ</p>
        <img src="/graficas/4_rho_vs_lambda.png?v={{ graf_version }}" alt="Rho vs Lambda">
      </div>

      <div class="graf-card">
        <p>Distribución de medias Wq — verificación TCL</p>
        <img src="/graficas/5_distribucion_medias_wq.png?v={{ graf_version }}" alt="TCL">
      </div>

      <div class="graf-card wide">
        <p>Heatmap análisis de sensibilidad</p>
        <img src="/graficas/6_heatmap_sensibilidad.png?v={{ graf_version }}" alt="Heatmap">
      </div>
    </div>
  </div>

  <!-- conclusiones ejecutivas -->
  <div class="section">
    <h2>Conclusiones Ejecutivas</h2>

    <div style="
        background:var(--surface);
        border:1px solid var(--border);
        border-radius:8px;
        padding:1.5rem;
    ">

      <h3 style="
          color:var(--accent);
          margin-bottom:1rem;
          font-family:'IBM Plex Mono',monospace;
      ">
        Recomendación Operativa
      </h3>

      <p style="margin-bottom:1rem;">
        El sistema actual opera con <strong>{{ c }} técnicos</strong> y presenta
        un tiempo promedio de espera de
        <strong>{{ wq_med }} minutos</strong>,
        valor superior al objetivo operacional de 10 minutos.
      </p>

      <p style="margin-bottom:1rem;">
        La utilización observada fue de
        <strong>{{ rho_pct }}%</strong>,
        indicando que los recursos disponibles trabajan cerca de su capacidad máxima.
      </p>

      <p style="margin-bottom:1rem;">
        El análisis de sensibilidad demuestra que el sistema es altamente sensible
        al crecimiento de la demanda. Con tres técnicos, tasas de llegada iguales
        o superiores a 12 clientes por hora generan escenarios inestables.
      </p>

      <p style="margin-bottom:1rem;">
        Los resultados indican que aumentar la capacidad a
        <strong>4 técnicos</strong>
        reduce significativamente los tiempos de espera y permite cumplir
        el nivel de servicio esperado.
      </p>

      <div style="
          margin-top:1rem;
          padding:1rem;
          border-left:4px solid var(--accent);
          background:#0f1d18;
          border-radius:4px;
      ">
        <strong>Conclusión Final:</strong><br><br>

        El sistema actual con {{ c }} técnicos no garantiza tiempos de espera
        inferiores a 10 minutos para todos los escenarios analizados.

        Se recomienda operar con un mínimo de
        <strong>4 técnicos</strong>
        para mantener estabilidad operativa, reducir la congestión y mejorar
        la experiencia del cliente.

        Si se espera crecimiento futuro de la demanda, una configuración de
        <strong>5 técnicos</strong>
        proporciona un margen adicional de capacidad.
      </div>

    </div>
  </div>

  <!-- reporte consola -->
  <div class="section">
    <h2>Reporte de consola</h2>
    <pre>{{ reporte }}</pre>
  </div>

</main>
</body>
</html>
"""


# ── rutas ──────────────────────────────────────────────────────────────────

def convertir_a_minutos(valor, unidad):
    valor = float(valor)
    unidad = (unidad or UNIDAD_T_SIM).lower()

    if unidad in ("seg", "segundos", "s"):
        return valor / 60.0
    if unidad in ("min", "minutos", "m"):
        return valor
    if unidad in ("hora", "horas", "h"):
        return valor * 60.0

    raise ValueError("unidad de tiempo no valida")


def normalizar_unidad_tiempo(unidad):
    unidad = (unidad or UNIDAD_T_SIM).lower()
    if unidad in ("seg", "segundos", "s"):
        return "seg"
    if unidad in ("min", "minutos", "m"):
        return "min"
    if unidad in ("hora", "horas", "h"):
        return "horas"
    raise ValueError("unidad de tiempo no valida")


@app.route("/", methods=["GET", "POST"])
def home():

    def fmt(v, d=2):
        return f"{v:.{d}f}"

    def render_error(
        mensaje,
        lam=LAM_BASE,
        mu=MU_BASE,
        c=C_BASE,
        n_rep=N_REP,
        t_sim_valor=T_SIM,
        t_sim_unidad=UNIDAD_T_SIM,
        t_sim=T_SIM,
        rho_pct="0",
        estado_mensaje=None,
        estado_tipo="ok",
    ):
        return render_template_string(
            HTML,
            n_rep=n_rep,
            wq_med="N/A",
            wq_inf="N/A",
            wq_sup="N/A",
            lq_med="N/A",
            rho_pct=rho_pct,
            rho_bar_pct=min(float(rho_pct), 100.0),
            wq_teo="N/A",
            n_min="N/A",
            lam=lam,
            mu=mu,
            c=c,
            t_sim_valor=t_sim_valor,
            t_sim_unidad=t_sim_unidad,
            t_sim=fmt(t_sim),
            tabla=[],
            graf_version="base",
            reporte=mensaje,
            estado_mensaje=mensaje,
            estado_tipo="error"
        ), 400

    if request.method == "POST":

        t_sim_valor_raw = request.form.get("t_sim_valor", T_SIM)
        t_sim_unidad_raw = request.form.get("t_sim_unidad", UNIDAD_T_SIM)

        try:
            lam = float(request.form.get("lam", ""))
            mu = float(request.form.get("mu", ""))
            c = int(request.form.get("c", ""))
            n_rep = int(request.form.get("n_rep", ""))
            t_sim_valor = float(t_sim_valor_raw)
            t_sim_unidad = normalizar_unidad_tiempo(t_sim_unidad_raw)
            t_sim = convertir_a_minutos(t_sim_valor, t_sim_unidad)
        except (TypeError, ValueError):
            return render_error(
                "Error: todos los campos deben tener valores numericos validos.",
                t_sim_valor=t_sim_valor_raw,
                t_sim_unidad=t_sim_unidad_raw
            )

        if lam <= 0 or mu <= 0 or c <= 0 or n_rep <= 0 or t_sim <= 0:
            return render_error(
                "Error: lambda, mu, tecnicos, replicas y tiempo deben ser mayores que cero.",
                lam=lam,
                mu=mu,
                c=c,
                n_rep=n_rep,
                t_sim_valor=t_sim_valor,
                t_sim_unidad=t_sim_unidad,
                t_sim=t_sim
            )

        if t_sim <= T_WARM:
            return render_error(
                f"Error: el tiempo de ejecucion debe ser mayor que el calentamiento ({T_WARM:.0f} min).",
                lam=lam,
                mu=mu,
                c=c,
                n_rep=n_rep,
                t_sim_valor=t_sim_valor,
                t_sim_unidad=t_sim_unidad,
                t_sim=t_sim
            )

        # Verificar estabilidad
        rho = lam / (c * mu)

        if rho >= 1:
            return render_error(
                f"Error: sistema inestable. rho = {rho:.3f}. Debe cumplirse lambda < c*mu.",
                lam=lam,
                mu=mu,
                c=c,
                n_rep=n_rep,
                t_sim_valor=t_sim_valor,
                t_sim_unidad=t_sim_unidad,
                t_sim=t_sim,
                rho_pct=fmt(rho * 100, 1)
            )

        mc = correr_replicas(
            N=n_rep,
            lam=lam,
            mu=mu,
            c=c,
            t_sim=t_sim,
            t_warm=T_WARM,
            semilla_base=SEMILLA
        )

        teo = calcular_mmc(lam, mu, c)

        comp = comparar_con_simulacion(
            lam,
            mu,
            c,
            mc["resumen"]
        )

        r = mc["resumen"]
        generar_graficas(lam, mu, c, mc, t_sim=t_sim, t_warm=T_WARM)
        graf_version = f"{lam}-{mu}-{c}-{n_rep}-{t_sim}"

        return render_template_string(
            HTML,
            n_rep=n_rep,
            wq_med=fmt(r["wq_promedio"]["media"]),
            wq_inf=fmt(r["wq_promedio"]["ic_inferior"]),
            wq_sup=fmt(r["wq_promedio"]["ic_superior"]),
            lq_med=fmt(r["lq_promedio"]["media"]),
            rho_pct=fmt(r["rho"]["media"] * 100, 1),
            rho_bar_pct=min(r["rho"]["media"] * 100, 100.0),
            wq_teo=fmt(teo["Wq"]),
            n_min=mc["n_minimo"],
            lam=lam,
            mu=mu,
            c=c,
            t_sim_valor=t_sim_valor,
            t_sim_unidad=t_sim_unidad,
            t_sim=fmt(t_sim),
            tabla=comp,
            graf_version=graf_version,
            reporte=REPORTE_CONSOLA or "(sin salida de consola)",
            estado_mensaje="Simulacion calculada correctamente.",
            estado_tipo="ok"
        )

    # GET inicial
    r = _mc["resumen"]

    return render_template_string(
        HTML,
        n_rep=N_REP,
        wq_med=fmt(r["wq_promedio"]["media"]),
        wq_inf=fmt(r["wq_promedio"]["ic_inferior"]),
        wq_sup=fmt(r["wq_promedio"]["ic_superior"]),
        lq_med=fmt(r["lq_promedio"]["media"]),
        rho_pct=fmt(r["rho"]["media"] * 100, 1),
        rho_bar_pct=min(r["rho"]["media"] * 100, 100.0),
        wq_teo=fmt(_teo["Wq"]),
        n_min=_mc["n_minimo"],
        lam=LAM_BASE,
        mu=MU_BASE,
        c=C_BASE,
        t_sim_valor=T_SIM,
        t_sim_unidad=UNIDAD_T_SIM,
        t_sim=fmt(T_SIM),
        tabla=_comp,
        graf_version="base",
        reporte=REPORTE_CONSOLA or "(sin salida de consola)",
        estado_mensaje=None,
        estado_tipo="ok"
    )
    
@app.route("/health")
def health():
    return jsonify({"status": "ok", "servicio": "TechClassUC Simulator"}), 200

@app.route("/simular", methods=["POST"])
def simular():
    try:
        b = request.get_json(force=True) or {}
        lam = float(b.get("lam", LAM_BASE)); mu = float(b.get("mu", MU_BASE))
        c = int(b.get("c", C_BASE)); N = int(b.get("N", N_REP))
        if "t_sim_valor" in b:
            t_sim = convertir_a_minutos(b.get("t_sim_valor"), b.get("t_sim_unidad", UNIDAD_T_SIM))
        else:
            t_sim = float(b.get("t_sim", T_SIM))
        t_warm = float(b.get("t_warm", T_WARM))
        if lam <= 0 or mu <= 0 or c <= 0 or N <= 0 or t_sim <= 0:
            return jsonify({"error": "lam, mu, c, N y t_sim deben ser mayores que cero"}), 400
        if t_warm < 0 or t_warm >= t_sim:
            return jsonify({"error": "t_warm debe ser mayor o igual a cero y menor que t_sim"}), 400
        if lam / (c * mu) >= 1:
            return jsonify({"error": f"Sistema inestable ρ={lam/(c*mu):.3f}"}), 400
        res = correr_replicas(N=N, lam=lam, mu=mu, c=c,
                              t_sim=t_sim,
                              t_warm=t_warm,
                              semilla_base=int(b.get("semilla", SEMILLA)))
        return jsonify({"resumen": res["resumen"], "n_minimo": res["n_minimo"], "t_sim": t_sim}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/analitico", methods=["POST"])
def analitico():
    try:
        b = request.get_json(force=True) or {}
        res = calcular_mmc(float(b.get("lam", LAM_BASE)),
                           float(b.get("mu",  MU_BASE)),
                           int(b.get("c", C_BASE)))
        if res is None:
            return jsonify({"error": "Sistema inestable"}), 400
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sensibilidad", methods=["POST"])
def sensibilidad():
    try:
        import numpy as np
        b = request.get_json(force=True) or {}
        sens = analisis_sensibilidad(mu=float(b.get("mu", MU_BASE)),
                                     N=int(b.get("N", 15)),
                                     c_valores=b.get("c_valores", [2,3,4,5]),
                                     lam_valores=b.get("lam_valores", [8,10,12,14,16]))
        def serial(v):
            if isinstance(v, np.ndarray): return v.tolist()
            if isinstance(v, (np.integer,)): return int(v)
            if isinstance(v, (np.floating,)): return None if np.isnan(v) else float(v)
            return v
        return jsonify({k: serial(v) for k,v in sens.items() if k != "resultados"}), 200
    except Exception as e:
        return jsonify({"error": str(e), "detalle": traceback.format_exc()}), 500

@app.route("/comparar", methods=["POST"])
def comparar():
    try:
        b = request.get_json(force=True) or {}
        lam=float(b.get("lam",LAM_BASE)); mu=float(b.get("mu",MU_BASE)); c=int(b.get("c",C_BASE))
        if lam/(c*mu)>=1: return jsonify({"error":"inestable"}),400
        mc = correr_replicas(N=int(b.get("N",N_REP)), lam=lam, mu=mu, c=c)
        return jsonify(comparar_con_simulacion(lam, mu, c, mc["resumen"])), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/graficas/<nombre>")
def grafica(nombre):
    ruta = os.path.join(GRAFICAS_DIR, nombre)
    if not os.path.exists(ruta):
        return jsonify({"error": "no encontrada"}), 404
    return send_file(ruta, mimetype="image/png")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
