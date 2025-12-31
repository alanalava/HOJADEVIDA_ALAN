from django.shortcuts import render
from .models import (
    DatosPersonales,
    ExperienciaLaboral,
    CursosRealizados,
    VentaGarage,
    Reconocimientos,
    ProductosAcademicos,
    ProductosLaborales
)

def get_active_profile():
    return DatosPersonales.objects.filter(perfilactivo=1).first()


def home(request):
    perfil = get_active_profile()
    context = {
        'perfil': perfil,
        'resumen_exp': ExperienciaLaboral.objects.filter(
            idperfilconqueestaactivo=perfil,
            activarparaqueseveaenfront=True
        )[:3],
        'resumen_cursos': CursosRealizados.objects.filter(
            idperfilconqueestaactivo=perfil,
            activarparaqueseveaenfront=True
        )[:3],
        'resumen_garage': VentaGarage.objects.filter(
            idperfilconqueestaactivo=perfil,
            activarparaqueseveaenfront=True
        )[:5],
        'resumen_rec': Reconocimientos.objects.filter(
            idperfilconqueestaactivo=perfil,
            activarparaqueseveaenfront=True
        )[:3],
        'resumen_acad': ProductosAcademicos.objects.filter(
            idperfilconqueestaactivo=perfil,
            activarparaqueseveaenfront=True
        )[:3],
        'resumen_lab': ProductosLaborales.objects.filter(
            idperfilconqueestaactivo=perfil,
            activarparaqueseveaenfront=True
        )[:3],
    }
    return render(request, 'home.html', context)


def experiencia(request):
    perfil = get_active_profile()
    datos = ExperienciaLaboral.objects.filter(
        idperfilconqueestaactivo=perfil,
        activarparaqueseveaenfront=True
    )
    return render(request, 'experiencia.html', {
        'perfil': perfil,
        'datos': datos
    })


def productos_academicos(request):
    perfil = get_active_profile()
    datos = ProductosAcademicos.objects.filter(
        idperfilconqueestaactivo=perfil,
        activarparaqueseveaenfront=True
    )
    return render(request, 'productos_academicos.html', {
        'perfil': perfil,
        'datos': datos
    })


def productos_laborales(request):
    perfil = get_active_profile()
    datos = ProductosLaborales.objects.filter(
        idperfilconqueestaactivo=perfil,
        activarparaqueseveaenfront=True
    ).order_by('-fechaproducto')
    return render(request, 'productos_laborales.html', {
        'perfil': perfil,
        'datos': datos
    })


def cursos(request):
    perfil = get_active_profile()
    datos = CursosRealizados.objects.filter(
        idperfilconqueestaactivo=perfil,
        activarparaqueseveaenfront=True
    )
    return render(request, 'cursos.html', {
        'perfil': perfil,
        'datos': datos
    })


def reconocimientos(request):
    perfil = get_active_profile()
    datos = Reconocimientos.objects.filter(
        idperfilconqueestaactivo=perfil,
        activarparaqueseveaenfront=True
    ).order_by('-fechareconocimiento')
    return render(request, 'reconocimientos.html', {
        'perfil': perfil,
        'datos': datos
    })


def garage(request):
    perfil = get_active_profile()
    datos = VentaGarage.objects.filter(
        idperfilconqueestaactivo=perfil,
        activarparaqueseveaenfront=True
    )
    return render(request, 'garage.html', {
        'perfil': perfil,
        'datos': datos
    })


# --- NUEVA FUNCIÓN AGREGADA ---
def cv_completo(request):
    perfil = get_active_profile()
    
    context = {
        'perfil': perfil,
        'experiencias': ExperienciaLaboral.objects.filter(
            idperfilconqueestaactivo=perfil, 
            activarparaqueseveaenfront=True
        ).order_by('-fechainiciogestion'),
        
        'cursos': CursosRealizados.objects.filter(
            idperfilconqueestaactivo=perfil, 
            activarparaqueseveaenfront=True
        ).order_by('-fechafin'),
        
        'reconocimientos': Reconocimientos.objects.filter(
            idperfilconqueestaactivo=perfil, 
            activarparaqueseveaenfront=True
        ).order_by('-fechareconocimiento'),
        
        'productos_acad': ProductosAcademicos.objects.filter(
            idperfilconqueestaactivo=perfil, 
            activarparaqueseveaenfront=True
        ),
        
        'productos_lab': ProductosLaborales.objects.filter(
            idperfilconqueestaactivo=perfil, 
            activarparaqueseveaenfront=True
        ).order_by('-fechaproducto'),
        
        'garage': VentaGarage.objects.filter(
            idperfilconqueestaactivo=perfil, 
            activarparaqueseveaenfront=True
        )
    }
    
    return render(request, 'cv_completo.html', context)