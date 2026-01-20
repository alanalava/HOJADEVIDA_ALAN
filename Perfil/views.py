from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from xhtml2pdf import pisa
from pypdf import PdfWriter, PdfReader
import os
import io
import requests

from .models import (
    DatosPersonales, ExperienciaLaboral, CursosRealizados, 
    VentaGarage, Reconocimientos, ProductosAcademicos, ProductosLaborales
)

# --- TU FUNCIÓN ORIGINAL PARA QUE XHTML2PDF LEA IMÁGENES ---
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

# --- FUNCIÓN SIMPLE: CONVIERTE CUALQUIER HTML A PDF EN MEMORIA ---
def html_a_pdf(html_string):
    buffer = io.BytesIO()
    pisa.CreatePDF(html_string, dest=buffer, link_callback=link_callback)
    buffer.seek(0)
    return buffer

def cv_completo(request):
    perfil = DatosPersonales.objects.filter(perfilactivo=1).first()
    
    # 1. GENERAMOS EL CV DE TEXTO (PRIMERAS PÁGINAS)
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
    # Agregamos el CV al PDF final
    merger.append(html_a_pdf(html_cv))

    # 2. LISTA DE COSAS PARA ADJUNTAR
    adjuntos = []
    # Recorremos para guardar (Titulo, URL)
    for x in context['experiencias']: 
        if x.rutacertificado: adjuntos.append((f"Experiencia: {x.cargodesempenado}", x.rutacertificado.url))
    for x in context['cursos']: 
        if x.rutacertificado: adjuntos.append((f"Curso: {x.nombrecurso}", x.rutacertificado.url))
    for x in context['recos']: 
        if x.rutacertificado: adjuntos.append((f"Logro: {x.descripcionreconocimiento}", x.rutacertificado.url))
    for x in context['garage']: 
        if x.documento_interes: adjuntos.append((f"Garage: {x.nombreproducto}", x.documento_interes.url))

    # 3. SI HAY ADJUNTOS, PONEMOS LA HOJA "ANEXOS"
    if adjuntos:
        html_separador = """
        <html><body style="font-family: Helvetica; text-align: center;">
            <br><br><br><br><br><br><br><br>
            <h1 style="font-size: 50px; color: #2563eb;">ANEXOS</h1>
            <p style="font-size: 20px; color: #666;">Documentos de Soporte</p>
        </body></html>
        """
        merger.append(html_a_pdf(html_separador))

        # 4. AGREGAMOS UNO POR UNO
        for titulo, url in adjuntos:
            try:
                # Descargamos el archivo para ver qué es
                response = requests.get(url, timeout=15)
                if response.status_code == 200:
                    archivo_bytes = io.BytesIO(response.content)
                    
                    # SI ES PDF: Lo pegamos directo
                    if url.lower().endswith('.pdf') or response.content.startswith(b'%PDF'):
                        # Primero una hoja con el título
                        html_titulo = f"<html><body><h2 style='color:#2563eb;'>{titulo}</h2><p>(Documento PDF a continuación)</p></body></html>"
                        merger.append(html_a_pdf(html_titulo))
                        merger.append(archivo_bytes)
                    
                    # SI ES IMAGEN: Creamos un HTML con la imagen y lo convertimos a PDF
                    # (Esto funcionaba antes, así que lo usamos igual)
                    else:
                        html_imagen = f"""
                        <html>
                            <body style="font-family: Helvetica; padding: 20px;">
                                <h2 style="color: #2563eb; border-bottom: 1px solid #ccc;">{titulo}</h2>
                                <br>
                                <div style="text-align: center;">
                                    <img src="{url}" style="max-width: 100%; max-height: 900px;">
                                </div>
                            </body>
                        </html>
                        """
                        merger.append(html_a_pdf(html_imagen))
            except Exception as e:
                print(f"Error adjuntando {titulo}: {e}")

    # 5. GENERAR EL PDF FINAL
    output = io.BytesIO()
    merger.write(output)
    merger.close()
    
    response = HttpResponse(output.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="CV_Final.pdf"'
    return response

# --- TUS VISTAS NORMALES (NO TOCAR) ---
def get_active_profile(): return DatosPersonales.objects.filter(perfilactivo=1).first()
def home(request): return render(request, 'home.html', {'perfil': get_active_profile(), 'resumen_exp': ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3], 'resumen_cursos': CursosRealizados.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3], 'resumen_garage': VentaGarage.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:5], 'resumen_rec': Reconocimientos.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3], 'resumen_acad': ProductosAcademicos.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3], 'resumen_lab': ProductosLaborales.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)[:3]})
def experiencia(request): return render(request, 'experiencia.html', {'perfil': get_active_profile(), 'datos': ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def productos_academicos(request): return render(request, 'productos_academicos.html', {'perfil': get_active_profile(), 'datos': ProductosAcademicos.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def productos_laborales(request): return render(request, 'productos_laborales.html', {'perfil': get_active_profile(), 'datos': ProductosLaborales.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def cursos(request): return render(request, 'cursos.html', {'perfil': get_active_profile(), 'datos': CursosRealizados.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def reconocimientos(request): return render(request, 'reconocimientos.html', {'perfil': get_active_profile(), 'datos': Reconocimientos.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})
def garage(request): return render(request, 'garage.html', {'perfil': get_active_profile(), 'datos': VentaGarage.objects.filter(idperfilconqueestaactivo=get_active_profile(), activarparaqueseveaenfront=True)})