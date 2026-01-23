from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from xhtml2pdf import pisa
from pypdf import PdfWriter
import os
import io
import requests

from .models import (
    DatosPersonales, ExperienciaLaboral, CursosRealizados, 
    VentaGarage, Reconocimientos, ProductosAcademicos, ProductosLaborales
)

# --- CALLBACK (INTACTO) ---
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
    return uri 

# --- CONVERTIR HTML A PDF (INTACTO) ---
def html_a_pdf(html_string):
    buffer = io.BytesIO()
    pisa.CreatePDF(html_string, dest=buffer, link_callback=link_callback)
    buffer.seek(0)
    return buffer

# --- CV COMPLETO (MODIFICADO PARA FILTROS) ---
def cv_completo(request):
    perfil = DatosPersonales.objects.filter(perfilactivo=1).first()
    
    # --- LOGICA DE FILTROS (NUEVO) ---
    # Si la URL tiene parametros (viene del modal), filtramos. Si no, mostramos todo.
    usar_filtros = len(request.GET) > 0
    
    inc_exp = request.GET.get('inc_exp') == 'on' or not usar_filtros
    inc_cur = request.GET.get('inc_cur') == 'on' or not usar_filtros
    inc_rec = request.GET.get('inc_rec') == 'on' or not usar_filtros
    inc_acad = request.GET.get('inc_acad') == 'on' or not usar_filtros
    inc_lab = request.GET.get('inc_lab') == 'on' or not usar_filtros
    inc_gar = request.GET.get('inc_gar') == 'on' or not usar_filtros

    # 1. GENERAR CV DE TEXTO (AQUÍ APLICAMOS LOS IF)
    context = {
        'perfil': perfil,
        'experiencias': ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechainiciogestion') if inc_exp else [],
        'cursos': CursosRealizados.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechafin') if inc_cur else [],
        'recos': Reconocimientos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechareconocimiento') if inc_rec else [],
        'garage': VentaGarage.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True) if inc_gar else [],
        'acad': ProductosAcademicos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True) if inc_acad else [],
        'lab': ProductosLaborales.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechaproducto') if inc_lab else []
    }

    template = get_template('cv_completo.html')
    html_cv = template.render(context)
    
    merger = PdfWriter()
    merger.append(html_a_pdf(html_cv))

    # 2. RECOLECTAR URLs (AUTOMATICAMENTE TOMA SOLO LO FILTRADO)
    urls_adjuntos = []
    
    for x in context['experiencias']: 
        if x.rutacertificado: urls_adjuntos.append(x.rutacertificado.url)
    for x in context['cursos']: 
        if x.rutacertificado: urls_adjuntos.append(x.rutacertificado.url)
    for x in context['recos']: 
        if x.rutacertificado: urls_adjuntos.append(x.rutacertificado.url)
    for x in context['garage']: 
        if x.documento_interes: urls_adjuntos.append(x.documento_interes.url)

    # 3. PROCESAR ANEXOS (INTACTO)
    if urls_adjuntos:
        html_separador = """
        <html><body style="font-family: Helvetica; text-align: center;">
            <br><br><br><br><br><br><br><br><br><br>
            <h1 style="font-size: 60px; color: #2563eb;">ANEXOS</h1>
            <p style="font-size: 20px; color: #666;">Documentos de Soporte</p>
        </body></html>
        """
        merger.append(html_a_pdf(html_separador))

        for url in urls_adjuntos:
            try:
                response = requests.get(url, timeout=15)
                if response.status_code == 200:
                    archivo_bytes = io.BytesIO(response.content)
                    if url.lower().endswith('.pdf') or response.content.startswith(b'%PDF'):
                        merger.append(archivo_bytes)
                    else:
                        html_imagen = f"""
                        <html>
                            <body style="margin: 0; padding: 0; text-align: center;">
                                <img src="{url}" style="width: 100%; max-height: 1000px; object-fit: contain;">
                            </body>
                        </html>
                        """
                        merger.append(html_a_pdf(html_imagen))
            except Exception as e:
                print(f"Error adjuntando {url}: {e}")

    # 4. SALIDA FINAL
    output = io.BytesIO()
    merger.write(output)
    merger.close()
    
    response = HttpResponse(output.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="CV_Final.pdf"'
    return response

# --- VISTAS NORMALES (INTACTAS) ---
def get_active_profile(): return DatosPersonales.objects.filter(perfilactivo=1).first()
def home(request): return render(request, 'home.html', {'perfil': get_active_profile(), 'resumen_exp': ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3], 'resumen_cursos': CursosRealizados.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3], 'resumen_garage': VentaGarage.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:5], 'resumen_rec': Reconocimientos.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3], 'resumen_acad': ProductosAcademicos.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3], 'resumen_lab': ProductosLaborales.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3]})
def experiencia(request): return render(request, 'experiencia.html', {'perfil': get_active_profile(), 'datos': ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def productos_academicos(request): return render(request, 'productos_academicos.html', {'perfil': get_active_profile(), 'datos': ProductosAcademicos.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def productos_laborales(request): return render(request, 'productos_laborales.html', {'perfil': get_active_profile(), 'datos': ProductosLaborales.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def cursos(request): return render(request, 'cursos.html', {'perfil': get_active_profile(), 'datos': CursosRealizados.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def reconocimientos(request): return render(request, 'reconocimientos.html', {'perfil': get_active_profile(), 'datos': Reconocimientos.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def garage(request): return render(request, 'garage.html', {'perfil': get_active_profile(), 'datos': VentaGarage.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})