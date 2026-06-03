import re
import unittest
from unittest.mock import patch

from montecarlo import correr_replicas
from analitico import calcular_mmc
from web_service import app, T_SIM, T_WARM, SEMILLA


def _metric_value(html, label):
    pattern = (
        rf'<div class="label">{re.escape(label)}</div>\s*'
        rf'<div class="value"[^>]*>([^<]+)</div>'
    )
    match = re.search(pattern, html)
    if not match:
        raise AssertionError(f"No se encontro la metrica {label!r}")
    return match.group(1).strip()


def _input_value(html, name):
    pattern = rf'name="{re.escape(name)}"\s+value="([^"]+)"'
    match = re.search(pattern, html)
    if not match:
        raise AssertionError(f"No se encontro el input {name!r}")
    return match.group(1)


def _selected_option(html, name):
    pattern = (
        rf'<select name="{re.escape(name)}">.*?'
        rf'<option value="([^"]+)" selected>'
    )
    match = re.search(pattern, html, re.S)
    if not match:
        raise AssertionError(f"No se encontro la opcion seleccionada de {name!r}")
    return match.group(1)


class WebServiceSimulationTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @patch("web_service.generar_graficas")
    def test_metricas_clave_se_actualizan_con_parametros_nuevos(self, _graficas):
        data = {"lam": "8", "mu": "4", "c": "3", "n_rep": "3", "t_sim_valor": "2", "t_sim_unidad": "horas"}
        response = self.client.post("/", data=data)

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        esperado = correr_replicas(
            N=3,
            lam=8.0,
            mu=4.0,
            c=3,
            t_sim=120.0,
            t_warm=T_WARM,
            semilla_base=SEMILLA,
        )
        resumen = esperado["resumen"]
        teorico = calcular_mmc(8.0, 4.0, 3)

        self.assertEqual(_input_value(html, "lam"), "8.0")
        self.assertEqual(_input_value(html, "mu"), "4.0")
        self.assertEqual(_input_value(html, "c"), "3")
        self.assertEqual(_input_value(html, "n_rep"), "3")
        self.assertEqual(_input_value(html, "t_sim_valor"), "2.0")
        self.assertEqual(_selected_option(html, "t_sim_unidad"), "horas")
        self.assertIn("Métricas clave &mdash; Montecarlo (3 réplicas)", html)

        self.assertEqual(
            _metric_value(html, "Wq simulado"),
            f'{resumen["wq_promedio"]["media"]:.2f} min',
        )
        self.assertEqual(
            _metric_value(html, "Lq simulado"),
            f'{resumen["lq_promedio"]["media"]:.2f}',
        )
        self.assertEqual(
            _metric_value(html, "Utilización ρ"),
            f'{resumen["rho"]["media"] * 100:.1f}%',
        )
        self.assertEqual(
            _metric_value(html, "Wq analítico"),
            f'{teorico["Wq"]:.2f} min',
        )

    @patch("web_service.generar_graficas")
    def test_dos_simulaciones_muestran_resultados_diferentes(self, _graficas):
        html_a = self.client.post(
            "/",
            data={"lam": "8", "mu": "4", "c": "3", "n_rep": "3", "t_sim_valor": "480", "t_sim_unidad": "min"},
        ).get_data(as_text=True)
        html_b = self.client.post(
            "/",
            data={"lam": "10", "mu": "4", "c": "4", "n_rep": "3", "t_sim_valor": "8", "t_sim_unidad": "horas"},
        ).get_data(as_text=True)

        self.assertNotEqual(
            _metric_value(html_a, "Wq simulado"),
            _metric_value(html_b, "Wq simulado"),
        )
        self.assertIn("/graficas/1_evolucion_temporal.png?v=8.0-4.0-3-3-480.0", html_a)
        self.assertIn("/graficas/1_evolucion_temporal.png?v=10.0-4.0-4-3-480.0", html_b)

    @patch("web_service.generar_graficas")
    def test_parametros_invalidos_no_muestran_metricas_viejas(self, _graficas):
        response = self.client.post(
            "/",
            data={"lam": "10", "mu": "4", "c": "0", "n_rep": "3", "t_sim_valor": "480", "t_sim_unidad": "min"},
        )

        self.assertEqual(response.status_code, 400)
        html = response.get_data(as_text=True)
        self.assertEqual(_metric_value(html, "Wq simulado"), "N/A min")
        self.assertEqual(_metric_value(html, "Lq simulado"), "N/A")
        self.assertEqual(_metric_value(html, "Wq analítico"), "N/A min")
        self.assertNotIn("<td>Wq</td>", html)

    @patch("web_service.generar_graficas")
    def test_sistema_inestable_muestra_error_visible_y_rho_real(self, _graficas):
        response = self.client.post(
            "/",
            data={"lam": "156", "mu": "4", "c": "3", "n_rep": "30", "t_sim_valor": "480", "t_sim_unidad": "min"},
        )

        self.assertEqual(response.status_code, 400)
        html = response.get_data(as_text=True)
        self.assertIn("Error: sistema inestable. rho = 13.000", html)
        self.assertEqual(_metric_value(html, "Utilización ρ"), "1300.0%")
        self.assertEqual(_metric_value(html, "Wq simulado"), "N/A min")

    @patch("web_service.generar_graficas")
    def test_tiempo_en_segundos_se_convierte_y_actualiza_la_vista(self, _graficas):
        html = self.client.post(
            "/",
            data={"lam": "8", "mu": "4", "c": "3", "n_rep": "3", "t_sim_valor": "7200", "t_sim_unidad": "seg"},
        ).get_data(as_text=True)

        esperado = correr_replicas(
            N=3,
            lam=8.0,
            mu=4.0,
            c=3,
            t_sim=120.0,
            t_warm=T_WARM,
            semilla_base=SEMILLA,
        )

        self.assertEqual(_input_value(html, "t_sim_valor"), "7200.0")
        self.assertEqual(_selected_option(html, "t_sim_unidad"), "seg")
        self.assertIn("120.00 min", html)
        self.assertEqual(
            _metric_value(html, "Wq simulado"),
            f'{esperado["resumen"]["wq_promedio"]["media"]:.2f} min',
        )

    def test_api_simular_acepta_tiempo_con_unidad(self):
        response = self.client.post(
            "/simular",
            json={"lam": 8, "mu": 4, "c": 3, "N": 3, "t_sim_valor": 2, "t_sim_unidad": "horas"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["t_sim"], 120.0)
        self.assertIn("wq_promedio", payload["resumen"])

    def test_api_simular_rechaza_tiempo_menor_al_calentamiento(self):
        response = self.client.post(
            "/simular",
            json={"lam": 8, "mu": 4, "c": 3, "N": 3, "t_sim_valor": 30, "t_sim_unidad": "min"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("t_warm", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
