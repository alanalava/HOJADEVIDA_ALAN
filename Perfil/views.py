from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from django.contrib.staticfiles import finders
from xhtml2pdf import pisa
from pypdf import PdfWriter
import os
import io
import requests  # <--- USAMOS ESTA LIBRERÍA AHORA, ES MEJOR

from .models import (
    DatosPersonales,
    ExperienciaLaboral,
    CursosRealizados,
    VentaGarage,
    Reconocimientos,
    ProductosAcademicos,
    ProductosLaborales
)

# --- FUNCIÓN PARA IMÁGENES LOCALES/NUBE (SIN CAMBIOS) ---
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

# --- HELPER PERFIL (SIN CAMBIOS) ---
def get_active_profile():
    return DatosPersonales.objects.filter(perfilactivo=1).first()

# --- VISTAS NORMALES (SIN CAMBIOS) ---
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

# --- VISTA PDF BLINDADA ---
def cv_completo(request):
    perfil = get_active_profile()
    
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
    
    # 1. Generar HTML
    template = get_template('cv_completo.html')
    html = template.render(context)
    
    # 2. Convertir a PDF en memoria
    main_pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=main_pdf_buffer, link_callback=link_callback)
    
    if pisa_status.err:
        return HttpResponse(f'Error generando PDF base: {html}')

    # 3. Iniciar Fusionador
    merger = PdfWriter()
    main_pdf_buffer.seek(0)
    merger.append(main_pdf_buffer)

    # --- FUNCIÓN DE DESCARGA ROBUSTA (USANDO REQUESTS) ---
    def adjuntar_pdf_externo(campo_archivo):
        if not campo_archivo: return
        url = campo_archivo.url
        
        # Detección flexible de PDF (ignora mayúsculas/parámetros url)
        if '.pdf' in url.lower():
            print(f"---- INTENTANDO DESCARGAR PDF: {url} ----") # LOG PARA RENDER
            try:
                # Usamos requests, que maneja mejor Cloudinary/SSL
                response = requests.get(url, stream=True, timeout=10)
                
                if response.status_code == 200:
                    # Convertimos los bytes descargados en un archivo en memoria
                    memory_file = io.BytesIO(response.content)
                    merger.append(memory_file)
                    print("  -> ¡ÉXITO! PDF adjuntado correctamente.")
                else:
                     print(f"  -> ERROR: El servidor devolvió código {response.status_code}")

            except Exception as e:
                # Este print saldrá en los logs de Render si algo falla
                print(f"  -> ERROR CRÍTICO descargando/uniendo PDF: {e}")
        else:
             print(f"---- Archivo ignorado (no parece PDF): {url} ----")

    # 4. Procesar adjuntos
    print("\nINICIANDO PROCESO DE ADJUNTOS...")
    for item in experiencias: adjuntar_pdf_externo(item.rutacertificado)
    for item in cursos_list: adjuntar_pdf_externo(item.rutacertificado)
    for item in reconocimientos_list: adjuntar_pdf_externo(item.rutacertificado)
    for item in garage_list: adjuntar_pdf_externo(item.documento_interes)
    print("FIN PROCESO DE ADJUNTOS.\n")

    # 5. Generar salida final
    final_output = io.BytesIO()
    merger.write(final_output)
    merger.close()
    
    response = HttpResponse(final_output.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="cv_completo_vFinal.pdf"'
    return response