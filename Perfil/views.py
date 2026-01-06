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

# --- FUNCIÓN PODEROSA PARA GESTIONAR IMÁGENES ---
def link_callback(uri, rel):
    # 1. Si es un archivo estático o media local
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

    # Si existe localmente, devolver ruta
    if os.path.isfile(path):
        return path

    # 2. Si es una URL remota (Cloudinary/Internet)
    if uri.startswith("http://") or uri.startswith("https://"):
        try:
            # Descargamos la imagen temporalmente
            response = requests.get(uri, stream=True, timeout=10)
            if response.status_code == 200:
                # Crear archivo temporal
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                temp_file.write(response.content)
                temp_file.close()
                return temp_file.name # Devolvemos la ruta del archivo temporal
        except Exception as e:
            print(f"Error descargando imagen para PDF: {e}")
            return uri # Si falla, devolvemos original por si acaso

    return uri

# --- VISTA PRINCIPAL DEL PDF ---
def cv_completo(request):
    perfil = DatosPersonales.objects.filter(perfilactivo=1).first()
    
    # Consultas
    experiencias = ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechainiciogestion')
    cursos = CursosRealizados.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechafin')
    recos = Reconocimientos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechareconocimiento')
    garage = VentaGarage.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)
    acad = ProductosAcademicos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)
    lab = ProductosLaborales.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True).order_by('-fechaproducto')

    # Preparamos contexto
    context = {
        'perfil': perfil, 'experiencias': experiencias, 'cursos': cursos,
        'reconocimientos': recos, 'garage': garage,
        'productos_acad': acad, 'productos_lab': lab
    }

    # 1. Generar HTML -> PDF Base
    template = get_template('cv_completo.html')
    html = template.render(context)
    
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer, link_callback=link_callback)
    
    if pisa_status.err:
        return HttpResponse(f'Error al generar PDF: {html}')

    # 2. Fusión de Adjuntos (Detectando si son PDF reales)
    merger = PdfWriter()
    pdf_buffer.seek(0)
    merger.append(pdf_buffer)

    def procesar_adjunto(archivo):
        if not archivo: return
        try:
            url = archivo.url
            # Descargamos el archivo a memoria
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                content = res.content
                # ¿ES UN PDF? (Miramos los "bytes mágicos" del inicio)
                if content.startswith(b'%PDF'):
                    print(f"-> Adjuntando PDF: {url}")
                    merger.append(io.BytesIO(content))
                else:
                    print(f"-> El archivo NO es un PDF, es imagen u otro: {url}")
        except Exception as e:
            print(f"Error procesando adjunto: {e}")

    # Recorremos todo lo que pueda tener certificado
    all_items = list(experiencias) + list(cursos) + list(recos) + list(garage)
    for item in all_items:
        # Algunos modelos usan 'rutacertificado', Garage usa 'documento_interes'
        if hasattr(item, 'rutacertificado'): procesar_adjunto(item.rutacertificado)
        if hasattr(item, 'documento_interes'): procesar_adjunto(item.documento_interes)

    # 3. Respuesta Final
    final_output = io.BytesIO()
    merger.write(final_output)
    
    response = HttpResponse(final_output.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="cv_completo_final.pdf"'
    return response

# --- RESTO DE VISTAS (NO CAMBIAN, PERO LAS DEJO PARA QUE NO SE ROMPA NADA) ---
def get_active_profile(): return DatosPersonales.objects.filter(perfilactivo=1).first()
def home(request): return render(request, 'home.html', {'perfil': get_active_profile()})
def experiencia(request): return render(request, 'experiencia.html', {'perfil': get_active_profile(), 'datos': ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=get_active_profile())})
def productos_academicos(request): return render(request, 'productos_academicos.html', {'perfil': get_active_profile(), 'datos': ProductosAcademicos.objects.filter(idperfilconqueestaactivo=get_active_profile())})
def productos_laborales(request): return render(request, 'productos_laborales.html', {'perfil': get_active_profile(), 'datos': ProductosLaborales.objects.filter(idperfilconqueestaactivo=get_active_profile())})
def cursos(request): return render(request, 'cursos.html', {'perfil': get_active_profile(), 'datos': CursosRealizados.objects.filter(idperfilconqueestaactivo=get_active_profile())})
def reconocimientos(request): return render(request, 'reconocimientos.html', {'perfil': get_active_profile(), 'datos': Reconocimientos.objects.filter(idperfilconqueestaactivo=get_active_profile())})
def garage(request): return render(request, 'garage.html', {'perfil': get_active_profile(), 'datos': VentaGarage.objects.filter(idperfilconqueestaactivo=get_active_profile())})