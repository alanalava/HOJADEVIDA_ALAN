from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from django.contrib.staticfiles import finders
from xhtml2pdf import pisa
from pypdf import PdfWriter
import os
import io
import requests
import tempfile

from .models import (
    DatosPersonales, ExperienciaLaboral, CursosRealizados, 
    VentaGarage, Reconocimientos, ProductosAcademicos, ProductosLaborales
)

# --- HELPER PARA IMÁGENES ---
def link_callback(uri, rel):
    sUrl = settings.STATIC_URL
    sRoot = settings.STATIC_ROOT
    mUrl = settings.MEDIA_URL
    mRoot = settings.MEDIA_ROOT

    if uri.startswith(mUrl):
        path = os.path.join(mRoot, uri.replace(mUrl, ""))
    elif uri.startswith(sUrl):
        path = os.path.join(sRoot, uri.replace(sUrl, ""))
    else:
        path = uri

    if os.path.isfile(path): return path

    # Para imágenes de internet (Cloudinary)
    if uri.startswith("http://") or uri.startswith("https://"):
        try:
            response = requests.get(uri, stream=True, timeout=10)
            if response.status_code == 200:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                temp_file.write(response.content)
                temp_file.close()
                return temp_file.name
        except: return uri
    return uri

# --- HELPER PARA CREAR PDFS PEQUEÑOS EN MEMORIA ---
def generar_hoja_html(html_string):
    buffer = io.BytesIO()
    pisa.CreatePDF(html_string, dest=buffer, link_callback=link_callback)
    buffer.seek(0)
    return buffer

# --- VISTA PRINCIPAL ---
def cv_completo(request):
    perfil = DatosPersonales.objects.filter(perfilactivo=1).first()
    
    # 1. GENERAR EL CV PRINCIPAL (SOLO TEXTO)
    context = {
        'perfil': perfil,
        'experiencias': ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechainiciogestion'),
        'cursos': CursosRealizados.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechafin'),
        'recos': Reconocimientos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechareconocimiento'),
        'garage': VentaGarage.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True),
        'acad': ProductosAcademicos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True),
        'lab': ProductosLaborales.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechaproducto')
    }

    template = get_template('cv_completo.html')
    html_cv = template.render(context)
    
    merger = PdfWriter()
    # Agregamos el CV base
    merger.append(generar_hoja_html(html_cv))

    # 2. RECOLECTAR TODOS LOS ADJUNTOS
    # Formato: (Título del anexo, URL del archivo)
    adjuntos = []
    
    for x in context['experiencias']: 
        if x.rutacertificado: adjuntos.append((f"Experiencia: {x.cargodesempenado}", x.rutacertificado.url))
    for x in context['cursos']: 
        if x.rutacertificado: adjuntos.append((f"Curso: {x.nombrecurso}", x.rutacertificado.url))
    for x in context['recos']: 
        if x.rutacertificado: adjuntos.append((f"Logro: {x.descripcionreconocimiento}", x.rutacertificado.url))
    for x in context['garage']: 
        if x.documento_interes: adjuntos.append((f"Garage: {x.nombreproducto}", x.documento_interes.url))

    # 3. PROCESAR ANEXOS SI EXISTEN
    if adjuntos:
        # A) Crear Hoja Separadora "ANEXOS"
        html_separador = """
        <html><body style="font-family: Helvetica; text-align: center;">
            <div style="padding-top: 40%;">
                <h1 style="font-size: 60px; color: #2563eb; margin: 0;">ANEXOS</h1>
                <hr style="width: 100px; border: 2px solid #333; margin: 20px auto;">
                <p style="font-size: 18px; color: #666;">Documentación de Soporte</p>
            </div>
        </body></html>
        """
        merger.append(generar_hoja_html(html_separador))

        # B) Recorrer cada adjunto
        for titulo, url in adjuntos:
            es_pdf = '.pdf' in url.lower()
            
            if es_pdf:
                # SI ES PDF: Ponemos una hoja de título antes
                html_titulo = f"""
                <html><body style="font-family: Helvetica; padding: 40px;">
                    <h2 style="color: #2563eb; border-bottom: 2px solid #ddd; padding-bottom: 10px;">ANEXO</h2>
                    <h3 style="font-size: 24px; color: #333;">{titulo}</h3>
                    <p style="margin-top: 50px; color: #666; font-style: italic;">
                        (El documento PDF se encuentra en la página siguiente)
                    </p>
                </body></html>
                """
                merger.append(generar_hoja_html(html_titulo))
                
                # Descargar y pegar el PDF real
                try:
                    res = requests.get(url, timeout=15)
                    if res.status_code == 200:
                        merger.append(io.BytesIO(res.content))
                except: pass
                
            else:
                # SI ES IMAGEN: La ponemos en la misma hoja con el título
                html_imagen = f"""
                <html><body style="font-family: Helvetica; padding: 40px;">
                    <h2 style="color: #2563eb; border-bottom: 2px solid #ddd; padding-bottom: 10px;">ANEXO</h2>
                    <h3 style="font-size: 20px; color: #333; margin-bottom: 30px;">{titulo}</h3>
                    
                    <div style="text-align: center; border: 1px solid #eee; padding: 10px; background: #fafafa;">
                        <img src="{url}" style="max-width: 100%; max-height: 800px;">
                    </div>
                </body></html>
                """
                merger.append(generar_hoja_html(html_imagen))

    # 4. FINALIZAR
    output = io.BytesIO()
    merger.write(output)
    merger.close()
    
    response = HttpResponse(output.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="CV_Completo_Anexos.pdf"'
    return response