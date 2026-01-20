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

from .models import (
    DatosPersonales, ExperienciaLaboral, CursosRealizados, 
    VentaGarage, Reconocimientos, ProductosAcademicos, ProductosLaborales
)

# --- TU LINK_CALLBACK ORIGINAL (El que funcionaba) ---
def link_callback(uri, rel):
    # Gestiona archivos estáticos y media locales
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

    # Si es local, devuelve la ruta
    if os.path.isfile(path):
        return path
    
    # Si es remoto (Cloudinary), xhtml2pdf lo manejará directamente
    return uri 

# --- HELPER SIMPLE ---
def generar_pdf_desde_html(html_string):
    buffer = io.BytesIO()
    # Aquí usamos tu callback original para que descargue las imágenes como antes
    pisa.CreatePDF(html_string, dest=buffer, link_callback=link_callback)
    buffer.seek(0)
    return buffer

# --- VISTA PRINCIPAL ---
def cv_completo(request):
    perfil = DatosPersonales.objects.filter(perfilactivo=1).first()
    
    # 1. PREPARAR DATOS
    context = {
        'perfil': perfil,
        'experiencias': ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechainiciogestion'),
        'cursos': CursosRealizados.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechafin'),
        'recos': Reconocimientos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechareconocimiento'),
        'garage': VentaGarage.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True),
        'acad': ProductosAcademicos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True),
        'lab': ProductosLaborales.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechaproducto')
    }

    # 2. GENERAR CV BASE (Solo texto, limpio)
    template = get_template('cv_completo.html')
    html_cv = template.render(context)
    
    merger = PdfWriter()
    merger.append(generar_pdf_desde_html(html_cv))

    # 3. IDENTIFICAR ANEXOS
    adjuntos = []
    # Recolectamos todo lo que tenga certificado/documento
    for x in context['experiencias']: 
        if x.rutacertificado: adjuntos.append((f"Experiencia: {x.cargodesempenado}", x.rutacertificado.url))
    for x in context['cursos']: 
        if x.rutacertificado: adjuntos.append((f"Curso: {x.nombrecurso}", x.rutacertificado.url))
    for x in context['recos']: 
        if x.rutacertificado: adjuntos.append((f"Logro: {x.descripcionreconocimiento}", x.rutacertificado.url))
    for x in context['garage']: 
        if x.documento_interes: adjuntos.append((f"Garage: {x.nombreproducto}", x.documento_interes.url))

    # 4. PROCESAR ANEXOS
    if adjuntos:
        # A) Hoja Separadora "ANEXOS"
        html_separador = """
        <html><body style="font-family: Helvetica; text-align: center;">
            <div style="padding-top: 40%;">
                <h1 style="font-size: 50px; color: #2563eb;">ANEXOS</h1>
                <hr style="width: 100px; margin: 20px auto;">
                <p style="color: #666;">Soportes y Certificados</p>
            </div>
        </body></html>
        """
        merger.append(generar_pdf_desde_html(html_separador))

        # B) Recorrer cada archivo
        for titulo, url in adjuntos:
            es_pdf = '.pdf' in url.lower()

            if es_pdf:
                # CASO 1: ES PDF (Ponemos título en una hoja y luego pegamos el PDF)
                html_titulo = f"""
                <html><body style="font-family: Helvetica; padding: 30px;">
                    <h2 style="color: #2563eb; border-bottom: 1px solid #ddd;">ANEXO</h2>
                    <h3>{titulo}</h3>
                    <p style="color:#666; font-style:italic; margin-top:20px;">(Documento PDF a continuación)</p>
                </body></html>
                """
                merger.append(generar_pdf_desde_html(html_titulo))
                
                # Descargar PDF real y adjuntar
                try:
                    res = requests.get(url, timeout=15)
                    if res.status_code == 200:
                        merger.append(io.BytesIO(res.content))
                except: pass

            else:
                # CASO 2: ES IMAGEN (Usamos el método que te funcionaba antes)
                # Creamos un HTML simple con la etiqueta <img> y dejamos que tu link_callback haga la magia
                html_imagen = f"""
                <html><body style="font-family: Helvetica; padding: 30px;">
                    <h2 style="color: #2563eb; border-bottom: 1px solid #ddd;">ANEXO</h2>
                    <h3 style="margin-bottom: 20px;">{titulo}</h3>
                    <div style="text-align: center; border: 1px solid #eee; padding: 10px;">
                        <img src="{url}" style="max-width: 100%; max-height: 850px;">
                    </div>
                </body></html>
                """
                # Al llamar a esta función, xhtml2pdf usará tu callback original para traer la imagen
                merger.append(generar_pdf_desde_html(html_imagen))

    # 5. FINALIZAR
    output = io.BytesIO()
    merger.write(output)
    merger.close()
    
    response = HttpResponse(output.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="CV_Final.pdf"'
    return response

# --- VISTAS NORMALES (Mantenlas para que no se rompa la web) ---
def get_active_profile(): return DatosPersonales.objects.filter(perfilactivo=1).first()
def home(request): return render(request, 'home.html', {'perfil': get_active_profile(), 'resumen_exp': ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3], 'resumen_cursos': CursosRealizados.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3], 'resumen_garage': VentaGarage.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:5], 'resumen_rec': Reconocimientos.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3], 'resumen_acad': ProductosAcademicos.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3], 'resumen_lab': ProductosLaborales.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3]})
def experiencia(request): return render(request, 'experiencia.html', {'perfil': get_active_profile(), 'datos': ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def productos_academicos(request): return render(request, 'productos_academicos.html', {'perfil': get_active_profile(), 'datos': ProductosAcademicos.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def productos_laborales(request): return render(request, 'productos_laborales.html', {'perfil': get_active_profile(), 'datos': ProductosLaborales.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def cursos(request): return render(request, 'cursos.html', {'perfil': get_active_profile(), 'datos': CursosRealizados.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def reconocimientos(request): return render(request, 'reconocimientos.html', {'perfil': get_active_profile(), 'datos': Reconocimientos.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def garage(request): return render(request, 'garage.html', {'perfil': get_active_profile(), 'datos': VentaGarage.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})