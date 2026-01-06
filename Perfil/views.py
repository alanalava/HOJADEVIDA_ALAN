from django.shortcuts import render
import os
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.contrib.staticfiles import finders

from .models import (
    DatosPersonales,
    ExperienciaLaboral,
    CursosRealizados,
    VentaGarage,
    Reconocimientos,
    ProductosAcademicos,
    ProductosLaborales
)

# --- FUNCIÓN CORREGIDA PARA NUBE (CLOUDINARY/AZURE) Y LOCAL ---
def link_callback(uri, rel):
    """
    Ayuda a xhtml2pdf a encontrar las imágenes, ya sean locales o en la nube.
    """
    # 1. Intentar buscar en STATIC (Archivos fijos como logos)
    result = finders.find(uri)
    if result:
        if isinstance(result, (list, tuple)):
            result = result[0]
        result = os.path.abspath(result)
        if os.path.isfile(result):
            return result

    # 2. Manejo de MEDIA (Tus fotos subidas)
    sUrl = settings.STATIC_URL
    sRoot = settings.STATIC_ROOT
    mUrl = settings.MEDIA_URL
    mRoot = settings.MEDIA_ROOT

    # Si es una URL completa (http/https), devolvemos tal cual para que la descargue
    if uri.startswith("http://") or uri.startswith("https://"):
        return uri

    # Si es ruta relativa local, intentamos construir el path
    if uri.startswith(mUrl):
        path = os.path.join(mRoot, uri.replace(mUrl, ""))
    elif uri.startswith(sUrl):
        path = os.path.join(sRoot, uri.replace(sUrl, ""))
    else:
        return uri

    # Si el archivo existe localmente, lo devolvemos. Si no, devolvemos la URI original.
    if os.path.isfile(path):
        return path
    
    return uri
# ----------------------------------------------------------

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

# --- VISTA PDF ---
def cv_completo(request):
    perfil = get_active_profile()
    
    context = {
        'perfil': perfil,
        'experiencias': ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechainiciogestion'),
        'cursos': CursosRealizados.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechafin'),
        'reconocimientos': Reconocimientos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechareconocimiento'),
        'productos_acad': ProductosAcademicos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True),
        'productos_lab': ProductosLaborales.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechaproducto'),
        'garage': VentaGarage.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)
    }
    
    template_path = 'cv_completo.html'
    # Usamos 'inline' para ver el PDF en el navegador primero
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="cv_completo.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(
       html, dest=response, link_callback=link_callback
    )

    if pisa_status.err:
       return HttpResponse('Hubo errores al generar el PDF <pre>' + html + '</pre>')
    
    return response