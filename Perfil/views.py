from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from django.contrib.staticfiles import finders
from xhtml2pdf import pisa
from pypdf import PdfWriter, PdfReader
import os
import io
import urllib.request # Para descargar los PDFs de la nube

from .models import (
    DatosPersonales,
    ExperienciaLaboral,
    CursosRealizados,
    VentaGarage,
    Reconocimientos,
    ProductosAcademicos,
    ProductosLaborales
)

# --- FUNCIÓN PARA IMÁGENES LOCALES/NUBE ---
def link_callback(uri, rel):
    result = finders.find(uri)
    if result:
        if isinstance(result, (list, tuple)): result = result[0]
        result = os.path.abspath(result)
        if os.path.isfile(result): return result

    sUrl = settings.STATIC_URL
    sRoot = settings.STATIC_ROOT
    mUrl = settings.MEDIA_URL
    mRoot = settings.MEDIA_ROOT

    if uri.startswith("http://") or uri.startswith("https://"): return uri
    
    if uri.startswith(mUrl): path = os.path.join(mRoot, uri.replace(mUrl, ""))
    elif uri.startswith(sUrl): path = os.path.join(sRoot, uri.replace(sUrl, ""))
    else: return uri

    if os.path.isfile(path): return path
    return uri

# --- FUNCIÓN HELPER PARA OBTENER PERFIL ---
def get_active_profile():
    return DatosPersonales.objects.filter(perfilactivo=1).first()

# --- VISTAS NORMALES ---
def home(request):
    perfil = get_active_profile()
    context = {
        'perfil': perfil,
        'resumen_exp': ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)[:3],
        'resumen_cursos': CursosRealizados.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)[:3],
        'resumen_garage': VentaGarage.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)[:5],
        'resumen_rec': Reconocimientos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)[:3],
        'resumen_acad': ProductosAcademicos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)[:3],
        'resumen_lab': ProductosLaborales.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)[:3],
    }
    return render(request, 'home.html', context)

def experiencia(request):
    perfil = get_active_profile()
    datos = ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)
    return render(request, 'experiencia.html', {'perfil': perfil, 'datos': datos})

def productos_academicos(request):
    perfil = get_active_profile()
    datos = ProductosAcademicos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)
    return render(request, 'productos_academicos.html', {'perfil': perfil, 'datos': datos})

def productos_laborales(request):
    perfil = get_active_profile()
    datos = ProductosLaborales.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechaproducto')
    return render(request, 'productos_laborales.html', {'perfil': perfil, 'datos': datos})

def cursos(request):
    perfil = get_active_profile()
    datos = CursosRealizados.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)
    return render(request, 'cursos.html', {'perfil': perfil, 'datos': datos})

def reconocimientos(request):
    perfil = get_active_profile()
    datos = Reconocimientos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechareconocimiento')
    return render(request, 'reconocimientos.html', {'perfil': perfil, 'datos': datos})

def garage(request):
    perfil = get_active_profile()
    datos = VentaGarage.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)
    return render(request, 'garage.html', {'perfil': perfil, 'datos': datos})

# --- VISTA PDF CON FUSIÓN (PYPDF) ---
def cv_completo(request):
    perfil = get_active_profile()
    
    # 1. Obtenemos datos
    experiencias = ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechainiciogestion')
    cursos_list = CursosRealizados.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechafin')
    reconocimientos_list = Reconocimientos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechareconocimiento')
    garage_list = VentaGarage.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)

    context = {
        'perfil': perfil,
        'experiencias': experiencias,
        'cursos': cursos_list,
        'reconocimientos': reconocimientos_list,
        'productos_acad': ProductosAcademicos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True),
        'productos_lab': ProductosLaborales.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechaproducto'),
        'garage': garage_list
    }
    
    # 2. Generar el PDF principal (HTML -> PDF) en memoria
    template_path = 'cv_completo.html'
    template = get_template(template_path)
    html = template.render(context)
    
    main_pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=main_pdf_buffer, link_callback=link_callback)
    
    if pisa_status.err:
        return HttpResponse('Hubo errores al generar el PDF principal <pre>' + html + '</pre>')

    # 3. Usar PyPDF para fusionar certificados
    merger = PdfWriter()
    
    # Agregamos primero el CV generado
    main_pdf_buffer.seek(0)
    merger.append(main_pdf_buffer)

    # Función interna para descargar y adjuntar si es PDF
    def adjuntar_pdf_externo(campo_archivo):
        if not campo_archivo: return
        try:
            url = campo_archivo.url
            # Solo procesamos si termina en .pdf
            if url.lower().endswith('.pdf'):
                # Descargamos el archivo a memoria
                remote_file = urllib.request.urlopen(url)
                memory_file = io.BytesIO(remote_file.read())
                merger.append(memory_file)
        except Exception as e:
            print(f"No se pudo adjuntar PDF: {e}")

    # Recorremos los modelos buscando PDFs
    for item in experiencias: adjuntar_pdf_externo(item.rutacertificado)
    for item in cursos_list: adjuntar_pdf_externo(item.rutacertificado)
    for item in reconocimientos_list: adjuntar_pdf_externo(item.rutacertificado)
    for item in garage_list: adjuntar_pdf_externo(item.documento_interes)

    # 4. Generar el archivo final fusionado
    final_output = io.BytesIO()
    merger.write(final_output)
    merger.close()
    
    # 5. Devolver respuesta
    response = HttpResponse(final_output.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="cv_completo_con_anexos.pdf"'
    return response