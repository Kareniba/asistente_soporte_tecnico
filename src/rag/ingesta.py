# src/rag/ingesta.py
import re
from pathlib import Path

from pypdf import PdfReader
from bs4 import BeautifulSoup
from docx import Document

from .config import DOCS_DIR


def _limpiar_markdown(texto: str) -> str:
    """Quita el front matter, las etiquetas Liquid y los enlaces de los .md de GitHub Docs."""
    texto = texto.replace("{% data variables.product.prodname_dotcom %}", "GitHub")

    titulo = ""
    m = re.match(r"^---\n(.*?)\n---\n", texto, flags=re.S)
    if m:
        t = re.search(r"^title:\s*(.+)$", m.group(1), flags=re.M)
        if t:
            titulo = re.sub(r"\{%.*?%\}|\{\{.*?\}\}", "", t.group(1)).strip().strip("'\"")
        texto = texto[m.end():]

    texto = re.sub(r"\{%.*?%\}", "", texto, flags=re.S)
    texto = re.sub(r"\{\{.*?\}\}", "", texto, flags=re.S)
    texto = re.sub(r"\[AUTOTITLE\]\([^)]*\)", "", texto)
    texto = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    return f"# {titulo}\n\n{texto}" if titulo else texto


def _leer_pdf(ruta: Path) -> list[dict]:
    lector = PdfReader(str(ruta))
    paginas = []
    for i, pagina in enumerate(lector.pages, start=1):
        texto = (pagina.extract_text() or "").strip()
        if texto:
            paginas.append({"texto": texto, "documento": ruta.name, "pagina": i})
    return paginas


def _leer_html(ruta: Path) -> list[dict]:
    html = ruta.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    for etiqueta in soup(["script", "style", "nav", "footer", "header"]):
        etiqueta.decompose()
    texto = soup.get_text(separator="\n").strip()
    return [{"texto": texto, "documento": ruta.name, "pagina": 1}] if texto else []


def _leer_docx(ruta: Path) -> list[dict]:
    doc = Document(str(ruta))
    texto = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [{"texto": texto, "documento": ruta.name, "pagina": 1}] if texto else []


def _leer_txt(ruta: Path) -> list[dict]:
    texto = ruta.read_text(encoding="utf-8", errors="ignore").strip()
    if ruta.suffix.lower() == ".md":
        texto = _limpiar_markdown(texto)
    return [{"texto": texto, "documento": ruta.name, "pagina": 1}] if texto else []


LECTORES = {
    ".pdf": _leer_pdf,
    ".html": _leer_html,
    ".htm": _leer_html,
    ".docx": _leer_docx,
    ".txt": _leer_txt,
    ".md": _leer_txt,
}


def cargar_documentos(directorio: Path = DOCS_DIR) -> list[dict]:
    """Recorre data/docs/ y devuelve una lista de {texto, documento, pagina}."""
    resultado = []
    for ruta in sorted(directorio.rglob("*")):
        lector = LECTORES.get(ruta.suffix.lower())
        if ruta.is_file() and lector:
            paginas = lector(ruta)
            print(f"[ingesta] {ruta.name}: {len(paginas)} página(s)/sección(es)")
            resultado.extend(paginas)
    return resultado


if __name__ == "__main__":
    docs = cargar_documentos()
    print(f"Total: {len(docs)} fragmentos de texto cargados")