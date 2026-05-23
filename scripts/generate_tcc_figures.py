"""
Gerador de figuras técnicas acadêmicas para TCC/artigo científico.
Sistema GeoMemorial — baseado na arquitetura real do repositório.
Gera 5 imagens PNG de alta qualidade (DPI 200, 16:9).
"""

from __future__ import annotations

import math
import os

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon

matplotlib.use("Agg")

OUT = "/mnt/ubuntu/ernesto/repos/tcc/docs/figuras_tcc"
os.makedirs(OUT, exist_ok=True)
DPI = 200

BG       = "#F8F9FA"
WHITE    = "#FFFFFF"
NAVY     = "#1A2E4A"
BLUE1    = "#2563EB"
BLUE2    = "#3B82F6"
BLUE3    = "#DBEAFE"
GREEN1   = "#16A34A"
GREEN2   = "#DCFCE7"
GRAY1    = "#374151"
GRAY2    = "#6B7280"
GRAY3    = "#E5E7EB"
GRAY4    = "#F3F4F6"
ORANGE1  = "#D97706"
ORANGE2  = "#FEF3C7"
PURPLE1  = "#7C3AED"
PURPLE2  = "#EDE9FE"
RED1     = "#DC2626"
CYAN1    = "#0891B2"
CYAN2    = "#CFFAFE"


def save(fig, name: str) -> None:
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  Saved → {name}")


def box(ax, x, y, w, h, label, sublabel="",
        color=BLUE3, border=BLUE2, fontsize=9,
        labelcolor=NAVY, radius=0.012, zorder=2):
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        linewidth=1.2, edgecolor=border, facecolor=color, zorder=zorder,
    )
    ax.add_patch(rect)
    cy = y + h / 2 + (0.012 if sublabel else 0)
    ax.text(x + w / 2, cy, label,
            ha="center", va="center",
            fontsize=fontsize, fontweight="bold",
            color=labelcolor, fontfamily="DejaVu Sans", zorder=zorder + 1)
    if sublabel:
        ax.text(x + w / 2, y + h / 2 - 0.014, sublabel,
                ha="center", va="center",
                fontsize=fontsize - 1.5, color=GRAY2,
                fontfamily="DejaVu Sans", zorder=zorder + 1)


def arr(ax, x0, y0, x1, y1, color=GRAY2, lw=1.2):
    ax.annotate(
        "", xy=(x1, y1), xytext=(x0, y0),
        arrowprops=dict(arrowstyle="-|>", color=color,
                        lw=lw, connectionstyle="arc3,rad=0.0"),
        zorder=1,
    )


def fig1_architecture() -> None:
    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.965, "Arquitetura Geral do Sistema GeoMemorial",
            ha="center", va="center",
            fontsize=15, fontweight="bold", color=NAVY, fontfamily="DejaVu Sans")
    ax.axhline(0.945, color=GRAY3, lw=1, xmin=0.04, xmax=0.96)
    def layer_bg(y, h, color, border, label, label_color):
        r = FancyBboxPatch((0.03, y), 0.94, h,
            boxstyle="round,pad=0,rounding_size=0.012",
            linewidth=1, edgecolor=border, facecolor=color,
            zorder=1, linestyle="--")
        ax.add_patch(r)
        ax.text(0.052, y + h - 0.017, label,
                fontsize=7.5, fontweight="bold",
                color=label_color, fontfamily="DejaVu Sans")
    layer_bg(0.815, 0.108, CYAN2, CYAN1,
             "CAMADA DE APRESENTAÇÃO  —  Navegador Web / HTML5 / CSS3 / JavaScript", CYAN1)
    bw, bh, by, gap = 0.128, 0.068, 0.835, 0.145
    x0 = 0.055
    labels_fe = [
        ("app.js", "Wizard 4 Etapas"),
        ("Leaflet.js", "Mapa / Polígono"),
        ("Upload", "CSV · TXT · ZIP"),
        ("styles.css", "Interface"),
        ("index.html", "Template Django"),
        ("Resultados", "Tabelas · Export"),
    ]
    for i, (la, lb) in enumerate(labels_fe):
        box(ax, x0 + i*gap, by, bw, bh, la, lb,
            color=CYAN2, border=CYAN1, fontsize=8)
    ax.annotate("", xy=(0.5, 0.810), xytext=(0.5, 0.780),
                arrowprops=dict(arrowstyle="-|>", color=BLUE2, lw=1.6))
    ax.text(0.514, 0.796, "HTTP / REST · CSRF", fontsize=7, color=GRAY2)
    layer_bg(0.545, 0.225, BLUE3, BLUE2,
             "CAMADA DE BACKEND  —  Django 5.2.2 · Python 3.12 · Gunicorn · WhiteNoise", BLUE1)
    vw, vh, vy = 0.145, 0.052, 0.692
    views = [
        ("core/views.py", "process_coordinates()\nexport_file()"),
        ("core/urls.py", "/api/process\n/api/export/<fmt>"),
        ("core/models.py", "Project · ProcessRun\nVertex · Artifact"),
        ("schemas.py", "Pydantic DTOs\nCoordinatePoint"),
        ("Migrations", "PostGIS SRID 31983\n0001–0007"),
        ("geomemorial/\nsettings.py", "PostgreSQL · S3\nALLOWED_HOSTS"),
    ]
    for i, (la, lb) in enumerate(views):
        box(ax, 0.055 + i*0.156, vy, 0.148, vh, la, lb,
            color=BLUE3, border=BLUE2, fontsize=7.5)
    sw, sh, sy = 0.098, 0.052, 0.613
    svcs = [
        ("geometry.py", "polygon_area()\nbuild_segments()"),
        ("angles.py", "decimal_to_dms()\nparse_azimuth()"),
        ("irradiation.py", "compute_\nirradiation()"),
        ("planimetry.py", "compute_planimetry\n_traverse()"),
        ("planimetric.py", "build_planimetric\n_table()"),
        ("processing.py", "process_traverse()\nprocess_coordinates()"),
        ("tolerances.py", "build_linear_adj()\nenrich_irradiation()"),
        ("reports.py", "export_pdf()\nexport_docx()\nexport_dxf()"),
    ]
    for i, (la, lb) in enumerate(svcs):
        box(ax, 0.055 + i*0.109, sy, 0.102, sh, la, lb,
            color=GREEN2, border=GREEN1, fontsize=7, labelcolor=GREEN1)
    stw, sth, sty = 0.17, 0.044, 0.557
    box(ax, 0.055, sty, stw, sth, "strategies/parsing.py",
        "CSV · TXT · ShapefileZIP", color=ORANGE2, border=ORANGE1, fontsize=8)
    box(ax, 0.235, sty, stw, sth, "strategies/export.py",
        "ExportStrategyFactory", color=ORANGE2, border=ORANGE1, fontsize=8)
    box(ax, 0.415, sty, 0.30, sth,
        "Libs: fpdf2 · python-docx · ezdxf · pyshp · pydantic",
        "", color=ORANGE2, border=ORANGE1, fontsize=8)
    box(ax, 0.725, sty, 0.245, sth,
        "Storage: filesystem / S3 / MinIO (boto3)",
        "", color=ORANGE2, border=ORANGE1, fontsize=8)
    ax.annotate("", xy=(0.5, 0.540), xytext=(0.5, 0.510),
                arrowprops=dict(arrowstyle="-|>", color=PURPLE1, lw=1.6))
    ax.text(0.514, 0.526, "Django ORM · psycopg2", fontsize=7, color=GRAY2)
    layer_bg(0.36, 0.130, PURPLE2, PURPLE1,
             "CAMADA DE DADOS  —  PostgreSQL 15 · PostGIS 3 · SRID 31983", PURPLE1)
    dw, dh, dy = 0.170, 0.070, 0.375
    db_items = [
        ("PostgreSQL 15", "Engine relacional\nACID"),
        ("PostGIS 3", "SRID 31983\nPointField · geom"),
        ("core_project", "name · owner · datum\nmeasurement_mode"),
        ("core_processrun", "area_m2 · perimeter_m\nclosure_error_m"),
        ("core_vertex", "vertex_code · x/y\nseq · geom"),
    ]
    for i, (la, lb) in enumerate(db_items):
        box(ax, 0.055 + i*0.188, dy, 0.180, dh, la, lb,
            color=PURPLE2, border=PURPLE1, fontsize=8)
    ax.annotate("", xy=(0.5, 0.355), xytext=(0.5, 0.325),
                arrowprops=dict(arrowstyle="-|>", color=GRAY2, lw=1.4))
    layer_bg(0.195, 0.115, GRAY4, GRAY2,
             "INFRAESTRUTURA  —  Docker · Docker Compose", GRAY1)
    cw, ch, cy2 = 0.192, 0.065, 0.212
    ct = [
        ("Container: web", "Django + Gunicorn\nentrypoint.sh"),
        ("Container: db", "PostgreSQL/PostGIS\nVol: db_data"),
        ("WhiteNoise", "Static files\nservidos pelo Django"),
        ("Volumes", "outputs/ · static/\nenv vars (.env)"),
        ("pytest + CI", "87+ testes unitários\ncobertura integração"),
    ]
    for i, (la, lb) in enumerate(ct):
        box(ax, 0.040 + i*0.195, cy2, 0.186, ch, la, lb,
            color=GRAY4, border=GRAY2, labelcolor=GRAY1, fontsize=8)
    ax.text(0.5, 0.040,
            "GeoMemorial · Sistema Automatizado de Georreferenciamento e Geração de Memoriais Descritivos"
            "  ·  Django 5.2 · PostGIS 3 · Python 3.12 · fpdf2 · ezdxf · python-docx · pyshp",
            ha="center", fontsize=6.8, color=GRAY2, fontfamily="DejaVu Sans")

    save(fig, "fig1_arquitetura_geral.png")


def fig2_flow() -> None:
    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.962,
            "Fluxo Automatizado de Processamento Espacial — GeoMemorial",
            ha="center", fontsize=14, fontweight="bold",
            color=NAVY, fontfamily="DejaVu Sans")
    ax.axhline(0.942, color=GRAY3, lw=1, xmin=0.04, xmax=0.96)

    BW, BH = 0.285, 0.056
    COL_L, COL_R = 0.08, 0.575

    def fbox(x, y, label, sub="", color=BLUE3, border=BLUE2):
        box(ax, x, y, BW, BH, label, sub, color=color, border=border,
            fontsize=8.5, radius=0.010)
    ax.text(COL_L + BW/2, 0.908, "MODO: IRRADIAÇÃO",
            ha="center", fontsize=9.5, fontweight="bold",
            color=CYAN1, fontfamily="DejaVu Sans")
    ax.text(COL_R + BW/2, 0.908, "MODO: LEVANTAMENTO PLANIMÉTRICO",
            ha="center", fontsize=9.5, fontweight="bold",
            color=BLUE1, fontfamily="DejaVu Sans")
    ir = [
        (0.843, "1. Entrada de Observações",
         "Vértice · Azimute · Distância\nEstação (X,Y) opcional",    CYAN2, CYAN1),
        (0.768, "2. Parsing (strategies/)",
         "TextIrradiationStrategy\nCsvTxtIrradiationStrategy",        CYAN2, CYAN1),
        (0.693, "3. Validação de Entrada",
         "validate_irradiation_input()\nhas_explicit_station AND",    GREEN2, GREEN1),
        (0.618, "4. Cálculo de Irradiação",
         "irradiation.py\nΔX=d·sin(Az) · ΔY=d·cos(Az)",             CYAN2, CYAN1),
        (0.543, "5. Geração de Pontos",
         "irradiation_to_points()\nPreserva ordem de entrada",        CYAN2, CYAN1),
        (0.468, "6. Validação Geométrica",
         "validate_points() · NaN/Inf check\nMAX_VERTICES = 5000",   GREEN2, GREEN1),
        (0.393, "7. Verificação de Fechamento",
         "is_closed(first, last)\nalready_closed check",              GREEN2, GREEN1),
        (0.318, "8. Enriquecimento de Erros",
         "enrich_irradiation_diagnostics()\ndE/dd=sin(Az) · dN/dAz=-d·sin(Az)", GREEN2, GREEN1),
    ]
    for (y, la, lb, c, b) in ir:
        fbox(COL_L, y, la, lb, color=c, border=b)
    for i in range(len(ir)-1):
        arr(ax, COL_L+BW/2, ir[i][0], COL_L+BW/2, ir[i+1][0]+BH,
            color=CYAN1, lw=1.4)
    pl = [
        (0.843, "1. Entrada de Observações",
         "Estação · Ponto visado · Ângulo · Distância",   BLUE3, BLUE2),
        (0.768, "2. Parsing (strategies/)",
         "TextCoordinatesStrategy\nCsvTxt · ShapefileZip", BLUE3, BLUE2),
        (0.693, "3. Azimute Inicial",
         "initial_azimuth_deg\nEquipmentErrorConfig",      BLUE3, BLUE2),
        (0.618, "4. Balanceamento Angular",
         "compute_planimetry_traverse()\nDistribuição equânime do erro", GREEN2, GREEN1),
        (0.543, "5. Otimização de Projeções",
         "_choose_projection_azimuths()\nMinimiza fechamento 2ⁿ orientações", GREEN2, GREEN1),
        (0.468, "6. Ajuste de Bowditch",
         "build_linear_adjustment_diagnostics()\nCx_i = −erro_E · (dist_i / perímetro)", GREEN2, GREEN1),
        (0.393, "7. Acumulação de Coordenadas",
         "ΔE = d·sin(Az) · ΔN = d·cos(Az)\nAdjusted X, Y por segmento", BLUE3, BLUE2),
        (0.318, "8. Tabela Planimétrica",
         "build_planimetric_calculation_table()\nΔE·ΔN brutos/corrigidos/ajustados", BLUE3, BLUE2),
    ]
    for (y, la, lb, c, b) in pl:
        fbox(COL_R, y, la, lb, color=c, border=b)
    for i in range(len(pl)-1):
        arr(ax, COL_R+BW/2, pl[i][0], COL_R+BW/2, pl[i+1][0]+BH,
            color=BLUE2, lw=1.4)
    ax.annotate("", xy=(0.500, 0.262+BH),
                xytext=(COL_L+BW/2, ir[-1][0]),
                arrowprops=dict(arrowstyle="-|>", color=CYAN1, lw=1.3,
                                connectionstyle="arc3,rad=0.18"))
    ax.annotate("", xy=(0.500, 0.262+BH),
                xytext=(COL_R+BW/2, pl[-1][0]),
                arrowprops=dict(arrowstyle="-|>", color=BLUE2, lw=1.3,
                                connectionstyle="arc3,rad=-0.18"))
    MID = 0.5 - BW/2
    common = [
        (0.258, "9. Cálculo de Área e Perímetro",
         "polygon_area() · Shoelace · signed_polygon_area()\npolygon_perimeter() · closure_error()",
         GREEN2, GREEN1),
        (0.183, "10. Validação Topológica",
         "validate_no_self_intersection() · build_segments()\nazimuth_to_bearing() · adaptive_epsilon()",
         GREEN2, GREEN1),
        (0.108, "11. Geração de Memorial + Exportação",
         "generate_memorial_text() · export_pdf/docx/dxf()\nfpdf2 · python-docx · ezdxf",
         ORANGE2, ORANGE1),
    ]
    for (y, la, lb, c, b) in common:
        box(ax, MID, y, BW, BH, la, lb, color=c, border=b,
            fontsize=8.5, radius=0.012)
    for i in range(len(common)-1):
        arr(ax, 0.5, common[i][0], 0.5, common[i+1][0]+BH,
            color=ORANGE1, lw=1.5)
    ax.text(0.5, 0.037,
            "processing.py · geometry.py · angles.py · planimetry.py · planimetric.py"
            " · tolerances.py · reports.py · strategies/",
            ha="center", fontsize=7, color=GRAY2, fontfamily="DejaVu Sans")

    save(fig, "fig2_fluxograma_processamento.png")


def fig3_interface() -> None:
    fig = plt.figure(figsize=(16, 9))
    fig.patch.set_facecolor(BG)
    tb = fig.add_axes([0.0, 0.905, 1.0, 0.095])
    tb.set_facecolor(NAVY)
    tb.axis("off")
    tb.text(0.018, 0.52, "GeoMemorial",
            fontsize=16, fontweight="bold", color=WHITE,
            fontfamily="DejaVu Sans", va="center")
    tb.text(0.185, 0.52,
            "Sistema Automatizado de Georreferenciamento e Memorial Descritivo",
            fontsize=8.5, color="#93C5FD", fontfamily="DejaVu Sans", va="center")
    for i, (tab, x) in enumerate([
        ("Identificação", 0.62), ("Coordenadas", 0.72),
        ("Processar", 0.82),    ("Resultados", 0.92),
    ]):
        active = (i == 3)
        tp = FancyBboxPatch((x-0.046, 0.14), 0.088, 0.65,
            boxstyle="round,pad=0,rounding_size=0.08",
            facecolor=BLUE1 if active else "#1E3A5F", edgecolor="none")
        tb.add_patch(tp)
        tb.text(x, 0.52, tab, ha="center", va="center",
                fontsize=8, fontweight="bold" if active else "normal",
                color=WHITE, fontfamily="DejaVu Sans")
    main = fig.add_axes([0.0, 0.0, 1.0, 0.905])
    main.set_facecolor(BG)
    main.set_xlim(0, 1)
    main.set_ylim(0, 1)
    main.axis("off")
    sb = FancyBboxPatch((0.012, 0.02), 0.192, 0.955,
        boxstyle="round,pad=0,rounding_size=0.010",
        facecolor=WHITE, edgecolor=GRAY3, lw=0.8, zorder=2)
    main.add_patch(sb)
    main.text(0.108, 0.940, "Resultados",
              ha="center", fontsize=8.5, fontweight="bold",
              color=NAVY, fontfamily="DejaVu Sans", va="center")
    main.axhline(0.922, color=GRAY3, lw=0.7, xmin=0.014, xmax=0.202)

    metrics = [
        ("Área Total",        "18.432,75 m²",     GREEN1),
        ("Equiv. (ha)",       "1,843275 ha",       GREEN1),
        ("Perímetro",         "593,42 m",          BLUE1),
        ("Erro Fechamento",   "0,003 m",           GREEN1),
        ("Modo",              "Planimétrico",       GRAY1),
        ("Vértices",          "8 pontos",           GRAY1),
        ("Datum",             "SIRGAS2000",         GRAY1),
        ("SRC",               "UTM 23S / 31983",    GRAY1),
    ]
    for i, (lbl, val, vc) in enumerate(metrics):
        y = 0.890 - i * 0.060
        mc = FancyBboxPatch((0.022, y-0.022), 0.170, 0.050,
            boxstyle="round,pad=0,rounding_size=0.007",
            facecolor=GRAY4, edgecolor=GRAY3, lw=0.5, zorder=3)
        main.add_patch(mc)
        main.text(0.032, y+0.003, lbl, fontsize=6.8, color=GRAY2,
                  fontfamily="DejaVu Sans", va="center")
        main.text(0.188, y+0.003, val, fontsize=7.5,
                  fontweight="bold", color=vc, fontfamily="DejaVu Sans",
                  va="center", ha="right")
    main.text(0.108, 0.402, "Exportar",
              ha="center", fontsize=8, fontweight="bold",
              color=NAVY, fontfamily="DejaVu Sans", va="center")
    for i, (fmt, col) in enumerate([("PDF", RED1), ("DOCX", BLUE1), ("DXF", ORANGE1)]):
        bx = 0.025 + i*0.064
        btn = FancyBboxPatch((bx, 0.353), 0.056, 0.040,
            boxstyle="round,pad=0,rounding_size=0.006",
            facecolor=col, edgecolor="none", zorder=3)
        main.add_patch(btn)
        main.text(bx+0.028, 0.373, fmt, ha="center", va="center",
                  fontsize=8, fontweight="bold",
                  color=WHITE, fontfamily="DejaVu Sans")
    main.text(0.108, 0.320, "Validação",
              ha="center", fontsize=8, fontweight="bold",
              color=NAVY, fontfamily="DejaVu Sans", va="center")
    val_items = [
        ("✓ Geometria válida",     GREEN1),
        ("✓ Fechamento OK",        GREEN1),
        ("✓ 8 vértices únicos",    GREEN1),
        ("✓ Err. linear < tol.",   GREEN1),
    ]
    for i, (txt, c) in enumerate(val_items):
        main.text(0.030, 0.294 - i*0.028, txt,
                  fontsize=7, color=c, fontfamily="DejaVu Sans", va="center")
    map_rect = FancyBboxPatch((0.218, 0.39), 0.440, 0.590,
        boxstyle="round,pad=0,rounding_size=0.010",
        facecolor="#EEF2FF", edgecolor=BLUE2, lw=1.0, zorder=2)
    main.add_patch(map_rect)
    for row in range(8):
        for col in range(8):
            shade = "#E8EEFF" if (row+col) % 2 == 0 else "#F0F4FF"
            tile = plt.Rectangle(
                (0.218 + col*0.055, 0.390 + row*0.0738),
                0.055, 0.0738, facecolor=shade, edgecolor="none", zorder=2)
            main.add_patch(tile)
    poly_xy = np.array([
        [0.340, 0.510], [0.415, 0.525], [0.490, 0.620],
        [0.530, 0.730], [0.478, 0.835], [0.398, 0.888],
        [0.318, 0.845], [0.280, 0.735], [0.288, 0.610],
        [0.340, 0.510],
    ])
    poly_patch = Polygon(poly_xy, closed=True,
                         facecolor="#BFDBFE", edgecolor=BLUE1,
                         linewidth=1.8, alpha=0.8, zorder=4)
    main.add_patch(poly_patch)
    for i, (vx, vy) in enumerate(poly_xy[:-1]):
        main.plot(vx, vy, "o", color=BLUE1, markersize=5, zorder=5)
        main.text(vx+0.008, vy+0.007, f"V{i+1:02d}",
                  fontsize=6.5, color=NAVY, fontweight="bold",
                  fontfamily="DejaVu Sans", zorder=6)
    nrx, nry = 0.630, 0.405
    main.annotate("", xy=(nrx, nry+0.048), xytext=(nrx, nry+0.005),
                  arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.2))
    main.text(nrx, nry+0.058, "N", ha="center", fontsize=9,
              fontweight="bold", color=NAVY, fontfamily="DejaVu Sans")
    circ = plt.Circle((nrx, nry+0.026), 0.024,
                       fill=False, edgecolor=NAVY, lw=0.7, zorder=4)
    main.add_patch(circ)

    main.text(0.222, 0.963,
              "Mapa — Visualização do Polígono Planimétrico (Leaflet.js / UTM SRID 31983)",
              fontsize=8, fontweight="bold", color=BLUE1, fontfamily="DejaVu Sans")
    tbl_x = 0.670
    tbl_rect = FancyBboxPatch((tbl_x, 0.39), 0.316, 0.590,
        boxstyle="round,pad=0,rounding_size=0.010",
        facecolor=WHITE, edgecolor=GRAY3, lw=0.8, zorder=2)
    main.add_patch(tbl_rect)
    main.text(tbl_x+0.158, 0.962, "Tabela de Segmentos",
              ha="center", fontsize=8, fontweight="bold",
              color=NAVY, fontfamily="DejaVu Sans", va="center")
    main.axhline(0.943, color=GRAY3, lw=0.5, xmin=0.672, xmax=0.984)

    hdrs = ["Seg.", "De → Para", "Dist.(m)", "Azimute", "Rumo"]
    hxs  = [tbl_x+0.006, tbl_x+0.040, tbl_x+0.128, tbl_x+0.198, tbl_x+0.254]
    for j, h in enumerate(hdrs):
        main.text(hxs[j], 0.922, h, fontsize=6.5, fontweight="bold",
                  color=NAVY, fontfamily="DejaVu Sans")
    main.axhline(0.909, color=GRAY3, lw=0.4, xmin=0.672, xmax=0.984)

    rows_tbl = [
        ("S01", "V01→V02", "73,42",  "042°13'18\"", "NE"),
        ("S02", "V02→V03", "91,85",  "087°55'41\"", "NE"),
        ("S03", "V03→V04", "108,23", "155°28'07\"", "SE"),
        ("S04", "V04→V05", "66,37",  "228°44'52\"", "SW"),
        ("S05", "V05→V06", "85,91",  "283°11'33\"", "NW"),
        ("S06", "V06→V07", "72,14",  "318°02'44\"", "NW"),
        ("S07", "V07→V08", "49,08",  "012°39'15\"", "NE"),
        ("S08", "V08→V01", "46,52",  "055°47'28\"", "NE"),
    ]
    for i, row in enumerate(rows_tbl):
        ry = 0.884 - i*0.063
        if i % 2 == 0:
            rb = FancyBboxPatch((tbl_x+0.005, ry-0.020), 0.302, 0.048,
                boxstyle="square,pad=0",
                facecolor=GRAY4, edgecolor="none", zorder=2)
            main.add_patch(rb)
        for j, val in enumerate(row):
            main.text(hxs[j], ry+0.005, val,
                      fontsize=6.5, color=GRAY1, fontfamily="DejaVu Sans")
    mem_rect = FancyBboxPatch((0.218, 0.022), 0.768, 0.345,
        boxstyle="round,pad=0,rounding_size=0.010",
        facecolor=WHITE, edgecolor=GRAY3, lw=0.8, zorder=2)
    main.add_patch(mem_rect)
    main.text(0.602, 0.345, "Memorial Descritivo Gerado Automaticamente",
              ha="center", fontsize=8.5, fontweight="bold",
              color=NAVY, fontfamily="DejaVu Sans", va="center")
    main.axhline(0.328, color=GRAY3, lw=0.5, xmin=0.220, xmax=0.984)

    mem_lines = [
        ("MEMORIAL DESCRITIVO — IMÓVEL: Fazenda Santo Antônio  |  PROPRIETÁRIO: João Carlos Silva", True),
        ("MUNICÍPIO: Campinas  |  ESTADO: SP  |  DATUM: SIRGAS2000  |  SRC: UTM Fuso 23S (SRID 31983)", True),
        ("", False),
        ("Inicia-se a descrição no vértice V01, de coordenadas E=240.523,18 m, N=7.458.312,45 m,", False),
        ("deste, segue confrontando com o Imóvel de Pedro Santos, pelo azimute 042°13'18\" (Rumo NE),", False),
        ("distância de 73,42 m, até o vértice V02, de coordenadas E=240.596,60 m, N=7.458.366,56 m.", False),
        ("Deste, segue confrontando com a Estrada Municipal EM-142, pelo azimute 087°55'41\" (Rumo NE),", False),
        ("distância de 91,85 m, até o vértice V03, de coordenadas E=240.688,45 m, N=7.458.370,01 m.", False),
        ("...", False),
        ("ÁREA TOTAL: 18.432,75 m²  (1,843275 ha)  |  PERÍMETRO: 593,42 m  |  ERRO DE FECHAMENTO: 0,003 m", True),
    ]
    for i, (line_txt, bold) in enumerate(mem_lines):
        y = 0.308 - i*0.027
        c = NAVY if bold else GRAY1
        if "ÁREA TOTAL" in line_txt:
            c = GREEN1
        main.text(0.230, y, line_txt,
                  fontsize=6.8, color=c,
                  fontweight="bold" if bold else "normal",
                  fontfamily="DejaVu Sans", va="center")

    save(fig, "fig3_interface_web.png")


def fig4_planimetric() -> None:
    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.axis("off")
    for lw, off in [(2.2, 0.0), (0.7, 0.013)]:
        r = plt.Rectangle((-0.040+off, -0.040+off),
                           1.08 - 2*off, 1.08 - 2*off,
                           fill=False, edgecolor=NAVY, lw=lw, zorder=10)
        ax.add_patch(r)

    # Coordenadas UTM reais (normalizadas)
    utm = np.array([
        [240523.18, 7458312.45],
        [240596.60, 7458366.56],
        [240688.45, 7458370.01],
        [240752.83, 7458262.84],
        [240706.91, 7458168.73],
        [240622.18, 7458149.30],
        [240540.05, 7458207.44],
        [240502.62, 7458288.91],
    ])
    names_v = [f"V{i+1:02d}" for i in range(len(utm))]
    xmin, ymin = utm.min(axis=0)
    xmax, ymax = utm.max(axis=0)
    span = max(xmax - xmin, ymax - ymin)

    def to_plot(xy):
        return (
            0.10 + (xy[0] - xmin) / span * 0.64,
            0.10 + (xy[1] - ymin) / span * 0.74,
        )

    ppts = np.array([to_plot(p) for p in utm])
    closed = np.vstack([ppts, ppts[0]])
    poly_p = Polygon(ppts, closed=True,
                     facecolor="#EEF2FF", edgecolor=NAVY,
                     linewidth=1.8, zorder=3)
    ax.add_patch(poly_p)
    for i in range(len(closed)-1):
        ax.plot([closed[i,0], closed[i+1,0]],
                [closed[i,1], closed[i+1,1]],
                color=NAVY, lw=1.8, zorder=4)

    # Offsets de rótulo por vértice (ajustados para não sobrepor)
    v_offs = [
        (-0.048, +0.012), (+0.018, +0.016),
        (+0.018, +0.010), (+0.020, -0.026),
        (+0.012, -0.032), (-0.040, -0.030),
        (-0.048, -0.012), (-0.050, +0.010),
    ]

    for i, (px, py) in enumerate(ppts):
        circ = plt.Circle((px, py), 0.013,
                           color=NAVY, fill=False, lw=1.4, zorder=5)
        ax.add_patch(circ)
        ax.plot(px, py, "o", color=NAVY, markersize=2.8, zorder=6)
        dx, dy = v_offs[i]
        ax.text(px+dx, py+dy, names_v[i],
                fontsize=8.5, fontweight="bold", color=NAVY,
                fontfamily="DejaVu Sans", zorder=7, va="center")
        cx, cy = utm[i]
        ax.text(px+dx, py+dy-0.028,
                f"E={cx:,.2f}\nN={cy:,.2f}",
                fontsize=5.8, color=GRAY2,
                fontfamily="DejaVu Sans Mono", va="top", zorder=7)
    for i in range(len(utm)):
        p0_u, p1_u = utm[i], utm[(i+1) % len(utm)]
        dx_u = p1_u[0] - p0_u[0]
        dy_u = p1_u[1] - p0_u[1]
        dist  = math.hypot(dx_u, dy_u)
        az_d  = math.degrees(math.atan2(dx_u, dy_u)) % 360
        dd, mm = int(az_d), int((az_d % 1)*60)
        ss = ((az_d % 1)*60 - mm) * 60
        az_str = f"{dd:03d}°{mm:02d}'{ss:05.2f}\""

        pp0, pp1 = ppts[i], ppts[(i+1) % len(ppts)]
        mx, my = (pp0[0]+pp1[0])/2, (pp0[1]+pp1[1])/2
        ang = math.atan2(pp1[1]-pp0[1], pp1[0]-pp0[0])
        nx_n = -math.sin(ang) * 0.036
        ny_n =  math.cos(ang) * 0.036
        ax.text(mx+nx_n, my+ny_n, f"{dist:.2f} m",
                ha="center", va="center", fontsize=7.5, color=BLUE1,
                fontweight="bold", fontfamily="DejaVu Sans",
                bbox=dict(boxstyle="round,pad=0.15", facecolor=WHITE,
                          edgecolor=BLUE2, lw=0.6, alpha=0.92), zorder=8)
        ax.text(mx+nx_n, my+ny_n-0.038, az_str,
                ha="center", va="center", fontsize=6, color=GRAY2,
                fontfamily="DejaVu Sans Mono", zorder=8)
    nx0, ny0 = 0.880, 0.760
    for ang2, lbl in [(0,"N"),(90,"E"),(180,"S"),(270,"W")]:
        r2 = math.radians(ang2)
        ax.annotate("", xy=(nx0+0.046*math.sin(r2), ny0+0.046*math.cos(r2)),
                    xytext=(nx0, ny0),
                    arrowprops=dict(
                        arrowstyle="-|>",
                        color=NAVY if ang2==0 else GRAY2,
                        lw=1.2 if ang2==0 else 0.7))
        ax.text(nx0+0.066*math.sin(r2), ny0+0.066*math.cos(r2),
                lbl, ha="center", va="center",
                fontsize=9 if ang2==0 else 7,
                fontweight="bold" if ang2==0 else "normal",
                color=NAVY if ang2==0 else GRAY2,
                fontfamily="DejaVu Sans")
    circ_n = plt.Circle((nx0, ny0), 0.026,
                         fill=False, edgecolor=NAVY, lw=0.7, zorder=5)
    ax.add_patch(circ_n)
    scx, scy = 0.790, 0.060
    for i in range(5):
        c = NAVY if i%2==0 else WHITE
        sr = plt.Rectangle((scx+i*0.025, scy), 0.025, 0.013,
                            facecolor=c, edgecolor=NAVY, lw=0.8, zorder=5)
        ax.add_patch(sr)
    for x_sc, lbl_sc in [(scx,"0"),(scx+0.075,"50"),(scx+0.125,"100 m")]:
        ax.text(x_sc, scy-0.016, lbl_sc, ha="center",
                fontsize=6.5, color=NAVY, fontfamily="DejaVu Sans")
    ax.text(scx+0.062, scy-0.030, "Escala 1:1000",
            ha="center", fontsize=7, fontweight="bold",
            color=NAVY, fontfamily="DejaVu Sans")
    leg = FancyBboxPatch((0.786, 0.115), 0.209, 0.205,
        boxstyle="round,pad=0,rounding_size=0.008",
        facecolor=WHITE, edgecolor=NAVY, lw=1.0, zorder=5)
    ax.add_patch(leg)
    ax.text(0.890, 0.303, "DADOS TÉCNICOS",
            ha="center", fontsize=7.5, fontweight="bold",
            color=NAVY, fontfamily="DejaVu Sans")
    ax.axhline(0.290, color=NAVY, lw=0.5, xmin=0.788, xmax=0.992)
    leg_data = [
        ("ÁREA TOTAL",      "18.432,75 m²"),
        ("Hectares",        "1,843275 ha"),
        ("PERÍMETRO",       "593,42 m"),
        ("Erro fechamento", "0,003 m"),
        ("Datum",           "SIRGAS2000"),
        ("SRC",             "UTM Fuso 23S"),
        ("SRID",            "31983"),
    ]
    for i, (k, v) in enumerate(leg_data):
        y = 0.278 - i*0.024
        ax.text(0.795, y, k, fontsize=6.5, color=GRAY2, fontfamily="DejaVu Sans")
        ax.text(0.990, y, v, fontsize=6.5, color=NAVY,
                fontweight="bold", ha="right", fontfamily="DejaVu Sans")
    crs = FancyBboxPatch((0.786, 0.335), 0.209, 0.370,
        boxstyle="round,pad=0,rounding_size=0.008",
        facecolor=NAVY, edgecolor=NAVY, lw=1.0, zorder=5)
    ax.add_patch(crs)
    ax.text(0.890, 0.688, "PLANTA",
            ha="center", fontsize=10.5, fontweight="bold",
            color=WHITE, fontfamily="DejaVu Sans")
    ax.text(0.890, 0.663, "PLANIMÉTRICA",
            ha="center", fontsize=10.5, fontweight="bold",
            color=WHITE, fontfamily="DejaVu Sans")
    ax.axhline(0.649, color="#4B6FA0", lw=0.5, xmin=0.789, xmax=0.992)
    stamp = [
        ("Imóvel:",       "Fazenda Santo Antônio"),
        ("Proprietário:", "João Carlos Silva"),
        ("Município:",    "Campinas — SP"),
        ("Datum:",        "SIRGAS2000"),
        ("Executado:",    "GeoMemorial v1.0"),
        ("Data:",         "Maio/2026"),
    ]
    for i, (k, v) in enumerate(stamp):
        y = 0.628 - i*0.044
        ax.text(0.795, y, k, fontsize=6.5, color="#93C5FD",
                fontfamily="DejaVu Sans")
        ax.text(0.795, y-0.020, v, fontsize=7, color=WHITE,
                fontweight="bold", fontfamily="DejaVu Sans")
    ax.text(0.38, 1.02,
            "Exemplo de Planta Planimétrica Gerada — Sistema GeoMemorial",
            ha="center", fontsize=12, fontweight="bold",
            color=NAVY, fontfamily="DejaVu Sans")

    save(fig, "fig4_planta_planimetrica.png")


def fig5_memorial() -> None:
    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor("#E8E8E8")
    ax.set_facecolor("#E8E8E8")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0.073, 0.023), 0.856, 0.927,
                                facecolor="#C0C0C0", edgecolor="none", zorder=0))
    ax.add_patch(plt.Rectangle((0.065, 0.033), 0.856, 0.930,
                                facecolor=WHITE, edgecolor=GRAY2, lw=0.8, zorder=1))
    for lw, off in [(1.5, 0.0), (0.5, 0.008)]:
        ax.add_patch(plt.Rectangle((0.085+off, 0.048+off),
                                    0.815-2*off, 0.900-2*off,
                                    fill=False, edgecolor=NAVY, lw=lw, zorder=2))

    def txt(x, y, s, ha="left", size=8, bold=False, color=GRAY1):
        ax.text(x, y, s, va="top", ha=ha,
                fontsize=size, fontweight="bold" if bold else "normal",
                color=color, fontfamily="DejaVu Sans", zorder=3)
    txt(0.493, 0.940, "MEMORIAL DESCRITIVO",
        ha="center", size=14, bold=True, color=NAVY)
    ax.axhline(0.912, color=NAVY, lw=1.5, xmin=0.088, xmax=0.912)
    ax.axhline(0.908, color=NAVY, lw=0.5, xmin=0.088, xmax=0.912)
    ax.add_patch(plt.Rectangle((0.095, 0.835), 0.795, 0.065,
                                facecolor=GRAY4, edgecolor=GRAY3, lw=0.5, zorder=2))
    txt(0.102, 0.892, "IMÓVEL: Fazenda Santo Antônio",
        size=8.5, bold=True, color=NAVY)
    txt(0.102, 0.867, "PROPRIETÁRIO: João Carlos Silva",
        size=8.5, bold=True, color=NAVY)
    txt(0.560, 0.892, "MUNICÍPIO: Campinas  |  ESTADO: SP",
        size=8.5, color=NAVY)
    txt(0.560, 0.867, "DATUM: SIRGAS2000  |  SRC: UTM Fuso 23S / SRID 31983",
        size=8.5, color=NAVY)
    ax.axhline(0.833, color=GRAY3, lw=0.5, xmin=0.088, xmax=0.912)
    txt(0.102, 0.820, "DESCRIÇÃO PERIMETRAL DO IMÓVEL",
        size=9, bold=True, color=NAVY)
    ax.axhline(0.804, color=NAVY, lw=0.5, xmin=0.098, xmax=0.580)
    intro = (
        "O imóvel objeto do presente memorial possui área total de 18.432,75 m² "
        "(equivalente a 1,843275 ha) e perímetro de 593,42 metros, localizado no "
        "Município de Campinas, Estado de São Paulo, posicionado no sistema de "
        "referência SIRGAS2000, projeção UTM Fuso 23S (SRID 31983). O levantamento "
        "topográfico foi realizado pelo método planimétrico com ajustamento de Bowditch."
    )
    words = intro.split()
    line, lines = "", []
    for w in words:
        if len(line) + len(w) < 108:
            line += w + " "
        else:
            lines.append(line.strip()); line = w + " "
    lines.append(line.strip())
    for i, ln in enumerate(lines):
        txt(0.102, 0.793 - i*0.022, ln, size=8, color=GRAY1)

    ax.axhline(0.747, color=GRAY3, lw=0.5, xmin=0.088, xmax=0.912)
    txt(0.102, 0.735, "COORDENADAS DOS VÉRTICES E SEGMENTOS DE DIVISA",
        size=9, bold=True, color=NAVY)
    ax.axhline(0.719, color=NAVY, lw=0.5, xmin=0.098, xmax=0.912)

    col_hdrs  = ["Vértice", "E (m)", "N (m)", "Seg.", "Azimute", "Rumo", "Dist. (m)", "Confrontante"]
    col_xs    = [0.102, 0.192, 0.288, 0.380, 0.438, 0.518, 0.600, 0.690]
    col_ws    = [0.082, 0.090, 0.090, 0.055, 0.077, 0.077, 0.085, 0.215]

    ax.add_patch(plt.Rectangle((0.097, 0.700), 0.800, 0.022,
                                facecolor=NAVY, edgecolor="none", zorder=2))
    for j, (h, cx, cw) in enumerate(zip(col_hdrs, col_xs, col_ws)):
        ax.text(cx + cw/2, 0.720, h, ha="center", va="top",
                fontsize=7, fontweight="bold", color=WHITE,
                fontfamily="DejaVu Sans", zorder=4)

    rows_mem = [
        ("V01","240.523,18","7.458.312,45","S01","042°13'18\"","N42°13'E","73,42","Imóvel Pedro Santos"),
        ("V02","240.596,60","7.458.366,56","S02","087°55'41\"","N87°55'E","91,85","Estrada Munic. EM-142"),
        ("V03","240.688,45","7.458.370,01","S03","155°28'07\"","S24°31'E","108,23","Imóvel Maria Oliveira"),
        ("V04","240.752,83","7.458.262,84","S04","228°44'52\"","S48°44'W","66,37","Córrego São Bento"),
        ("V05","240.706,91","7.458.168,73","S05","283°11'33\"","N76°48'W","85,91","Córrego São Bento"),
        ("V06","240.622,18","7.458.149,30","S06","318°02'44\"","N41°57'W","72,14","Imóvel Antônio Souza"),
        ("V07","240.540,05","7.458.207,44","S07","012°39'15\"","N12°39'E","49,08","Imóvel Antônio Souza"),
        ("V08","240.502,62","7.458.288,91","S08","055°47'28\"","N55°47'E","46,52","Imóvel Pedro Santos"),
    ]
    for i, row in enumerate(rows_mem):
        ry = 0.697 - i*0.026
        bg = GRAY4 if i%2==0 else WHITE
        ax.add_patch(plt.Rectangle((0.097, ry-0.012), 0.800, 0.026,
                                    facecolor=bg, edgecolor=GRAY3, lw=0.3, zorder=2))
        for j, (val, cx, cw) in enumerate(zip(row, col_xs, col_ws)):
            alg = "center" if j in (0,3,4,5) else "right" if j in (1,2,6) else "left"
            tx = cx+cw/2 if alg=="center" else cx+cw-0.004 if alg=="right" else cx+0.003
            c_val = BLUE1 if j==0 else ORANGE1 if j in (4,5) else GRAY1
            bold_v = j==0
            ax.text(tx, ry+0.008, val, ha=alg, va="top",
                    fontsize=6.8, color=c_val,
                    fontweight="bold" if bold_v else "normal",
                    fontfamily="DejaVu Sans", zorder=3)

    ax.axhline(0.488, color=NAVY, lw=0.5, xmin=0.088, xmax=0.912)
    txt(0.102, 0.477, "FECHAMENTO E CONCLUSÃO",
        size=9, bold=True, color=NAVY)
    ax.axhline(0.461, color=NAVY, lw=0.5, xmin=0.098, xmax=0.580)
    close_txt = (
        "O levantamento topográfico foi executado pelo método de poligonal fechada com ajustamento linear "
        "pelo método de Bowditch. O erro de fechamento linear obtido foi de 0,003 m, correspondendo a uma "
        "precisão relativa de 1:197.807, estando dentro dos limites aceitáveis para georreferenciamento rural "
        "conforme NBR 14166/1998. O presente memorial foi gerado automaticamente pelo Sistema GeoMemorial, "
        "com base nas observações de campo processadas computacionalmente via ajustamento paramétrico."
    )
    words2 = close_txt.split()
    line2, lines2 = "", []
    for w in words2:
        if len(line2)+len(w) < 110:
            line2 += w+" "
        else:
            lines2.append(line2.strip()); line2 = w+" "
    lines2.append(line2.strip())
    for i, ln in enumerate(lines2):
        txt(0.102, 0.449 - i*0.022, ln, size=8, color=GRAY1)
    ax.axhline(0.102, color=NAVY, lw=1.0, xmin=0.088, xmax=0.912)
    ax.axhline(0.099, color=NAVY, lw=0.4, xmin=0.088, xmax=0.912)
    for sx_sig, lbl_sig in [(0.155,"Responsável Técnico"),(0.493,"Proprietário"),(0.790,"Data")]:
        ax.axhline(0.079, color=GRAY2, lw=0.8,
                   xmin=sx_sig-0.075, xmax=sx_sig+0.075)
        ax.text(sx_sig, 0.072, lbl_sig, ha="center", va="top",
                fontsize=7, color=GRAY2, fontfamily="DejaVu Sans")
    ax.text(0.493, 0.060, "GeoMemorial — Sistema Automatizado  |  Gerado em: 17/05/2026",
            ha="center", va="top", fontsize=6.5, color=GRAY2,
            fontfamily="DejaVu Sans")
    ax.text(0.493, 0.990,
            "Exemplo de Memorial Descritivo Gerado Automaticamente — Sistema GeoMemorial",
            ha="center", va="top", fontsize=11, fontweight="bold",
            color=NAVY, fontfamily="DejaVu Sans")

    save(fig, "fig5_memorial_descritivo.png")


if __name__ == "__main__":
    print("Gerando figuras TCC — GeoMemorial…")
    fig1_architecture()
    fig2_flow()
    fig3_interface()
    fig4_planimetric()
    fig5_memorial()
    print(f"\nFiguras salvas em: {OUT}")
