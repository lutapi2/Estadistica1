#!/usr/bin/env python3
"""
================================================================================
BACKEND REST API — PROYECTO FINAL ESTADÍSTICA DESCRIPTIVA (CECAR)
SABER 11 SUCRE — ANÁLISIS EXPLORATORIO DE DATOS
================================================================================
Institución: Corporación Universitaria del Caribe - CECAR
Programa: Ingeniería de Sistemas
Docente: Mg. Sindy Velásquez Restrepo
Autores: Lucas Tapia Suárez, Daniel Cataño, José David Navarro, Eder Luis Zapa

Servidor HTTP nativo en Python 3 con SQLite integrado (sin dependencias externas).
Ejecutar con: python3 app.py
================================================================================
"""

import http.server
import socketserver
import json
import sqlite3
import urllib.parse
import os
import sys
import math

PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "saber11_sucre.db")
SQL_PATH = os.path.join(BASE_DIR, "saber11_sucre.sql")
INDEX_PATH = os.path.join(BASE_DIR, "index.html")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = MEMORY;")
    conn.execute("PRAGMA synchronous = OFF;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db_if_needed():
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        print(f"[*] Base de datos no encontrada en {DB_PATH}. Creando a partir de SQL...")
        if os.path.exists(SQL_PATH):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("PRAGMA journal_mode = MEMORY;")
            conn.execute("PRAGMA synchronous = OFF;")
            with open(SQL_PATH, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.close()
            print("[✓] Base de datos creada y poblada exitosamente.")
        else:
            print("[!] Advertencia: No se encontró saber11_sucre.sql.")

class Saber11RequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Habilitar CORS
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Ruta Raíz -> Servir index.html
        if path == "/" or path == "/index.html":
            if os.path.exists(INDEX_PATH):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(INDEX_PATH, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_json(404, {"error": "Archivo index.html no encontrado"})
                return

        # Descargas de archivos
        if path == "/download/sql":
            if os.path.exists(SQL_PATH):
                self.send_file_download(SQL_PATH, "saber11_sucre.sql", "application/sql")
                return
        if path == "/download/db":
            if os.path.exists(DB_PATH):
                self.send_file_download(DB_PATH, "saber11_sucre.db", "application/x-sqlite3")
                return

        # Endpoints de API REST
        if path == "/api/status":
            self.handle_status()
        elif path == "/api/estudiantes":
            self.handle_estudiantes(query)
        elif path == "/api/estadisticas":
            self.handle_estadisticas()
        elif path == "/api/frecuencias-no-agrupadas":
            self.handle_frecuencias_no_agrupadas()
        elif path == "/api/frecuencias-agrupadas":
            self.handle_frecuencias_agrupadas()
        elif path == "/api/brechas":
            self.handle_brechas()
        elif path == "/api/correlacion":
            self.handle_correlacion()
        elif path == "/api/municipios":
            self.handle_municipios()
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/api/query":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                body = json.loads(post_data.decode("utf-8"))
                sql = body.get("sql", "").strip()
                # Permitir únicamente consultas SELECT de lectura segura
                if not sql.upper().startswith("SELECT"):
                    self.send_json(400, {"error": "Solo se permiten consultas de lectura (SELECT)."})
                    return
                conn = get_db()
                c = conn.cursor()
                c.execute(sql)
                rows = [dict(r) for r in c.fetchall()[:200]]  # límite de 200 filas por seguridad
                cols = [desc[0] for desc in c.description] if c.description else []
                conn.close()
                self.send_json(200, {"columns": cols, "rows": rows, "count": len(rows)})
            except Exception as e:
                self.send_json(400, {"error": str(e)})
        else:
            self.send_json(404, {"error": "Endpoint no encontrado"})

    def send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def send_file_download(self, file_path, filename, mime):
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(os.path.getsize(file_path)))
        self.end_headers()
        with open(file_path, "rb") as f:
            self.wfile.write(f.read())

    def handle_status(self):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM saber11_sucre")
        count = c.fetchone()[0]
        conn.close()
        self.send_json(200, {
            "status": "online",
            "institucion": "Corporación Universitaria del Caribe - CECAR",
            "programa": "Ingeniería de Sistemas",
            "asignatura": "Estadística Descriptiva y Probabilidad",
            "docente": "Mg. Sindy Velásquez Restrepo",
            "integrantes": ["Lucas Tapia Suárez", "Daniel Cataño", "José David Navarro", "Eder Luis Zapa Centanaro"],
            "base_datos": "saber11_sucre.db",
            "total_registros": count,
            "servidor": "Python 3 Native HTTP Server"
        })

    def handle_estudiantes(self, query):
        conn = get_db()
        c = conn.cursor()

        page = int(query.get("page", [1])[0])
        limit = min(int(query.get("limit", [20])[0]), 100)
        offset = (page - 1) * limit

        where_clauses = []
        params = []

        if "mcpio" in query and query["mcpio"][0]:
            where_clauses.append("estu_mcpio_reside = ?")
            params.append(query["mcpio"][0])
        if "estrato" in query and query["estrato"][0]:
            where_clauses.append("fami_estratovivienda = ?")
            params.append(query["estrato"][0])
        if "genero" in query and query["genero"][0]:
            where_clauses.append("estu_genero = ?")
            params.append(query["genero"][0])
        if "naturaleza" in query and query["naturaleza"][0]:
            where_clauses.append("cole_naturaleza = ?")
            params.append(query["naturaleza"][0])
        if "q" in query and query["q"][0]:
            term = f"%{query['q'][0]}%"
            where_clauses.append("(estu_mcpio_reside LIKE ? OR fami_estratovivienda LIKE ? OR cole_naturaleza LIKE ?)")
            params.extend([term, term, term])

        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Conteo total filtrado
        c.execute(f"SELECT COUNT(*) FROM saber11_sucre{where_sql}", params)
        total_filtered = c.fetchone()[0]

        # Ordenación
        sort_by = query.get("sort_by", ["id"])[0]
        order = query.get("order", ["asc"])[0].upper()
        valid_cols = ["id", "punt_global", "punt_matematicas", "punt_lectura_critica", "punt_c_naturales", "punt_sociales_ciudadanas", "punt_ingles", "estu_mcpio_reside", "fami_estratovivienda"]
        if sort_by not in valid_cols:
            sort_by = "id"
        if order not in ["ASC", "DESC"]:
            order = "ASC"

        # Consulta paginada
        sql = f"SELECT * FROM saber11_sucre{where_sql} ORDER BY {sort_by} {order} LIMIT ? OFFSET ?"
        c.execute(sql, params + [limit, offset])
        rows = [dict(r) for r in c.fetchall()]
        conn.close()

        self.send_json(200, {
            "total": total_filtered,
            "page": page,
            "limit": limit,
            "total_pages": math.ceil(total_filtered / limit) if total_filtered > 0 else 1,
            "data": rows
        })

    def handle_estadisticas(self):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT punt_global, punt_matematicas, punt_lectura_critica, punt_c_naturales, punt_sociales_ciudadanas, punt_ingles FROM saber11_sucre ORDER BY punt_global ASC")
        rows = c.fetchall()
        conn.close()

        puntajes = [r["punt_global"] for r in rows]
        n = len(puntajes)
        media = sum(puntajes) / n
        mediana = (puntajes[n//2] if n % 2 != 0 else (puntajes[n//2 - 1] + puntajes[n//2]) / 2)
        
        # Moda
        counts = {}
        for p in puntajes:
            counts[p] = counts.get(p, 0) + 1
        moda = max(counts, key=counts.get)
        
        # Varianza y Desv Estándar
        var_s = sum((p - media) ** 2 for p in puntajes) / (n - 1)
        std_s = math.sqrt(var_s)
        cv = (std_s / media) * 100

        # Percentiles exactos
        def get_percentile(data, pct):
            k = (len(data) - 1) * (pct / 100.0)
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return data[int(k)]
            d0 = data[int(f)] * (c - k)
            d1 = data[int(c)] * (k - f)
            return d0 + d1

        q1 = get_percentile(puntajes, 25)
        q3 = get_percentile(puntajes, 75)
        p10 = get_percentile(puntajes, 10)
        p90 = get_percentile(puntajes, 90)
        p95 = get_percentile(puntajes, 95)

        # Promedios por materia
        prom_materias = {
            "lectura": round(sum(r["punt_lectura_critica"] for r in rows) / n, 2),
            "matematicas": round(sum(r["punt_matematicas"] for r in rows) / n, 2),
            "naturales": round(sum(r["punt_c_naturales"] for r in rows) / n, 2),
            "sociales": round(sum(r["punt_sociales_ciudadanas"] for r in rows) / n, 2),
            "ingles": round(sum(r["punt_ingles"] for r in rows) / n, 2)
        }

        self.send_json(200, {
            "n": n,
            "min": min(puntajes),
            "max": max(puntajes),
            "rango": max(puntajes) - min(puntajes),
            "media": round(media, 2),
            "mediana": round(mediana, 2),
            "moda": round(moda, 2),
            "varianza": round(var_s, 2),
            "desviacion_estandar": round(std_s, 2),
            "coeficiente_variacion": round(cv, 2),
            "q1": round(q1, 2),
            "q2": round(mediana, 2),
            "q3": round(q3, 2),
            "iqr": round(q3 - q1, 2),
            "p10": round(p10, 2),
            "p90": round(p90, 2),
            "p95": round(p95, 2),
            "materias": prom_materias
        })

    def handle_frecuencias_no_agrupadas(self):
        conn = get_db()
        c = conn.cursor()
        
        # Total
        c.execute("SELECT COUNT(*) FROM saber11_sucre")
        n = c.fetchone()[0]

        # Género
        c.execute("SELECT estu_genero, COUNT(*) as fi FROM saber11_sucre GROUP BY estu_genero ORDER BY fi DESC")
        genero_rows = c.fetchall()
        genero = []
        F_acc = 0
        for r in genero_rows:
            f_val = r["fi"]
            F_acc += f_val
            genero.append({
                "categoria": "Femenino" if r["estu_genero"] == "F" else "Masculino",
                "codigo": r["estu_genero"],
                "fi": f_val,
                "Fi": F_acc,
                "hi": round(f_val / n, 4),
                "Hi": round(F_acc / n, 4),
                "hi_pct": round((f_val / n) * 100, 2),
                "Hi_pct": round((F_acc / n) * 100, 2)
            })

        # Estrato
        estrato_order = ['Estrato 1', 'Estrato 2', 'Estrato 3', 'Estrato 4', 'Estrato 5', 'Estrato 6', 'Sin Estrato']
        c.execute("SELECT fami_estratovivienda, COUNT(*) as fi FROM saber11_sucre GROUP BY fami_estratovivienda")
        estrato_dict = {r["fami_estratovivienda"]: r["fi"] for r in c.fetchall()}
        estrato = []
        F_acc = 0
        for e in estrato_order:
            f_val = estrato_dict.get(e, 0)
            F_acc += f_val
            estrato.append({
                "categoria": e,
                "fi": f_val,
                "Fi": F_acc,
                "hi": round(f_val / n, 4),
                "Hi": round(F_acc / n, 4),
                "hi_pct": round((f_val / n) * 100, 2),
                "Hi_pct": round((F_acc / n) * 100, 2)
            })

        # Naturaleza
        c.execute("SELECT cole_naturaleza, COUNT(*) as fi FROM saber11_sucre GROUP BY cole_naturaleza ORDER BY fi DESC")
        nat_rows = c.fetchall()
        naturaleza = []
        F_acc = 0
        for r in nat_rows:
            f_val = r["fi"]
            F_acc += f_val
            naturaleza.append({
                "categoria": r["cole_naturaleza"],
                "fi": f_val,
                "Fi": F_acc,
                "hi": round(f_val / n, 4),
                "Hi": round(F_acc / n, 4),
                "hi_pct": round((f_val / n) * 100, 2),
                "Hi_pct": round((F_acc / n) * 100, 2)
            })

        conn.close()
        self.send_json(200, {
            "total": n,
            "genero": genero,
            "estrato": estrato,
            "naturaleza": naturaleza
        })

    def handle_frecuencias_agrupadas(self):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT punt_global FROM saber11_sucre ORDER BY punt_global ASC")
        puntajes = [r["punt_global"] for r in c.fetchall()]
        conn.close()

        n = len(puntajes)
        x_min = min(puntajes)
        x_max = max(puntajes)
        rango = x_max - x_min
        k_sturges = 1 + 3.322 * math.log10(n)
        k = round(k_sturges) # 12
        amplitud = math.ceil(rango / k) # 24

        limites = [x_min + i * amplitud for i in range(k + 1)]
        intervalos = []
        F_acc = 0

        for i in range(k):
            low = limites[i]
            high = limites[i+1]
            if i == k - 1:
                f_val = sum(1 for p in puntajes if low <= p <= high)
                nombre = f"[{low} - {high}]"
            else:
                f_val = sum(1 for p in puntajes if low <= p < high)
                nombre = f"[{low} - {high})"
            
            F_acc += f_val
            mc = (low + high) / 2.0
            hi = f_val / n
            Hi = F_acc / n
            intervalos.append({
                "intervalo": nombre,
                "lim_inf": low,
                "lim_sup": high,
                "marca_clase": mc,
                "fi": f_val,
                "Fi": F_acc,
                "hi": round(hi, 4),
                "Hi": round(Hi, 4),
                "hi_pct": round(hi * 100, 2),
                "Hi_pct": round(Hi * 100, 2),
                "xi_fi": round(mc * f_val, 2)
            })

        self.send_json(200, {
            "n": n,
            "xmin": x_min,
            "xmax": x_max,
            "rango": rango,
            "k": k,
            "k_sturges_exacto": round(k_sturges, 4),
            "amplitud": amplitud,
            "intervalos": intervalos
        })

    def handle_brechas(self):
        conn = get_db()
        c = conn.cursor()

        # Por Naturaleza
        c.execute("SELECT cole_naturaleza, COUNT(*) as count, ROUND(AVG(punt_global), 2) as media, MIN(punt_global) as min, MAX(punt_global) as max FROM saber11_sucre GROUP BY cole_naturaleza")
        por_naturaleza = [dict(r) for r in c.fetchall()]

        # Por Estrato
        c.execute("SELECT fami_estratovivienda, COUNT(*) as count, ROUND(AVG(punt_global), 2) as media FROM saber11_sucre GROUP BY fami_estratovivienda ORDER BY media DESC")
        por_estrato = [dict(r) for r in c.fetchall()]

        # Por Municipio (Top 10)
        c.execute("SELECT estu_mcpio_reside, COUNT(*) as count, ROUND(AVG(punt_global), 2) as media FROM saber11_sucre GROUP BY estu_mcpio_reside ORDER BY count DESC LIMIT 10")
        por_municipio = [dict(r) for r in c.fetchall()]

        conn.close()
        self.send_json(200, {
            "por_naturaleza": por_naturaleza,
            "por_estrato": por_estrato,
            "por_municipio": por_municipio
        })

    def handle_correlacion(self):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT punt_lectura_critica, punt_matematicas, punt_c_naturales, punt_sociales_ciudadanas, punt_ingles, punt_global FROM saber11_sucre")
        rows = c.fetchall()
        conn.close()

        data = {
            "Lectura": [r["punt_lectura_critica"] for r in rows],
            "Matemáticas": [r["punt_matematicas"] for r in rows],
            "Naturales": [r["punt_c_naturales"] for r in rows],
            "Sociales": [r["punt_sociales_ciudadanas"] for r in rows],
            "Inglés": [r["punt_ingles"] for r in rows],
            "Puntaje Global": [r["punt_global"] for r in rows]
        }

        # Pearson r
        def pearson(x, y):
            n = len(x)
            mx = sum(x) / n
            my = sum(y) / n
            num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
            den = math.sqrt(sum((xi - mx) ** 2 for xi in x) * sum((yi - my) ** 2 for yi in y))
            return round(num / den, 3) if den != 0 else 0.0

        keys = list(data.keys())
        matrix = {}
        for k1 in keys:
            matrix[k1] = {}
            for k2 in keys:
                matrix[k1][k2] = pearson(data[k1], data[k2])

        self.send_json(200, {"variables": keys, "matriz": matrix})

    def handle_municipios(self):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT DISTINCT estu_mcpio_reside FROM saber11_sucre ORDER BY estu_mcpio_reside ASC")
        muni = [r[0] for r in c.fetchall()]
        conn.close()
        self.send_json(200, {"municipios": muni})

if __name__ == "__main__":
    init_db_if_needed()
    with socketserver.TCPServer(("", PORT), Saber11RequestHandler) as httpd:
        print(f"================================================================================")
        print(f" SERVIDOR BACKEND ACTIVO — PROYECTO ESTADÍSTICA SABER 11 SUCRE")
        print(f" URL Local: http://localhost:{PORT}")
        print(f" API Endpoints:")
        print(f"   - GET  /api/status                   -> Estado y metadatos")
        print(f"   - GET  /api/estudiantes              -> Listado con filtros y paginación")
        print(f"   - GET  /api/estadisticas             -> Resumen paramétrico y estadígrafos")
        print(f"   - GET  /api/frecuencias-no-agrupadas -> Tablas de frecuencias no agrupadas")
        print(f"   - GET  /api/frecuencias-agrupadas    -> Tabla de Sturges (12 intervalos)")
        print(f"   - GET  /api/brechas                  -> Brechas por naturaleza, estrato y mcpio")
        print(f"   - GET  /api/correlacion              -> Matriz de correlación de Pearson")
        print(f"   - POST /api/query                    -> Consola SQL interactiva (SELECT)")
        print(f"   - GET  /download/sql                 -> Descargar saber11_sucre.sql")
        print(f"   - GET  /download/db                  -> Descargar saber11_sucre.db")
        print(f"================================================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido por el usuario.")
            httpd.server_close()
