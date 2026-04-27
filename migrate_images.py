#!/usr/bin/env python3
"""
Script para renombrar imágenes "_migrated" a nombres consistentes sin el sufijo.

Uso: python migrate_images.py
"""
import os
import sys
import time
from pathlib import Path

# Añadir el directorio raíz al path para importar modelos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dockerlabs.extensions import db as alchemy_db
from dockerlabs.models import User, Machine

def get_file_timestamp(filepath):
    """Obtiene el timestamp de modificación del archivo."""
    try:
        stat = os.stat(filepath)
        return int(stat.st_mtime)
    except:
        return int(time.time())

def migrate_profile_images():
    """Migra imágenes de perfil de usuario."""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    perfiles_dir = os.path.join(base_dir, 'database', 'almacenamiento', 'perfiles')
    
    users = User.query.filter(User.profile_image_path.like('%migrated%')).all()
    print(f"Encontrados {len(users)} usuarios con imágenes '_migrated'")
    
    migrated = 0
    errors = []
    
    for user in users:
        old_path = user.profile_image_path
        if not old_path or '_migrated' not in old_path:
            continue
        
        # Extraer extensión
        old_filename = os.path.basename(old_path)
        name_part, ext = os.path.splitext(old_filename)
        
        # Nuevo nombre: user_{id}_{timestamp}{ext}
        old_full_path = os.path.join(base_dir, old_path)
        ts = get_file_timestamp(old_full_path) if os.path.exists(old_full_path) else int(time.time())
        new_filename = f"user_{user.id}_{ts}{ext}"
        new_path = f"database/almacenamiento/perfiles/{new_filename}"
        new_full_path = os.path.join(base_dir, new_path)
        
        try:
            # Renombrar archivo si existe
            if os.path.exists(old_full_path):
                os.rename(old_full_path, new_full_path)
                print(f"✓ Renombrado: {old_filename} -> {new_filename}")
            else:
                print(f"⚠ Archivo no encontrado: {old_full_path}")
                errors.append(f"Usuario {user.id}: archivo no encontrado {old_full_path}")
            
            # Actualizar base de datos
            user.profile_image_path = new_path
            migrated += 1
            
        except Exception as e:
            error_msg = f"Error migrando usuario {user.id}: {e}"
            print(f"✗ {error_msg}")
            errors.append(error_msg)
    
    # Commit de cambios
    if migrated > 0:
        try:
            alchemy_db.session.commit()
            print(f"\n✓ Base de datos actualizada: {migrated} registros de usuarios")
        except Exception as e:
            alchemy_db.session.rollback()
            print(f"\n✗ Error al guardar en base de datos: {e}")
            return 0, errors
    
    return migrated, errors

def migrate_machine_logos():
    """Migra logos de máquinas."""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    logos_dir = os.path.join(base_dir, 'database', 'almacenamiento', 'logos')
    
    machines = Machine.query.filter(Machine.logo_path.like('%migrated%')).all()
    print(f"\nEncontradas {len(machines)} máquinas con logos '_migrated'")
    
    migrated = 0
    errors = []
    
    for machine in machines:
        old_path = machine.logo_path
        if not old_path or '_migrated' not in old_path:
            continue
        
        # Extraer extensión
        old_filename = os.path.basename(old_path)
        name_part, ext = os.path.splitext(old_filename)
        
        # Determinar prefijo según origen
        if machine.origen == 'bunker':
            prefix = f"bunker_{machine.id}"
        else:
            prefix = f"docker_{machine.id}"
        
        # Nuevo nombre: {prefix}_{timestamp}{ext}
        old_full_path = os.path.join(base_dir, old_path)
        ts = get_file_timestamp(old_full_path) if os.path.exists(old_full_path) else int(time.time())
        new_filename = f"{prefix}_{ts}{ext}"
        new_path = f"database/almacenamiento/logos/{new_filename}"
        new_full_path = os.path.join(base_dir, new_path)
        
        try:
            # Renombrar archivo si existe
            if os.path.exists(old_full_path):
                os.rename(old_full_path, new_full_path)
                print(f"✓ Renombrado: {old_filename} -> {new_filename}")
            else:
                print(f"⚠ Archivo no encontrado: {old_full_path}")
                errors.append(f"Máquina {machine.id}: archivo no encontrado {old_full_path}")
            
            # Actualizar base de datos
            machine.logo_path = new_path
            migrated += 1
            
        except Exception as e:
            error_msg = f"Error migrando máquina {machine.id}: {e}"
            print(f"✗ {error_msg}")
            errors.append(error_msg)
    
    # Commit de cambios
    if migrated > 0:
        try:
            alchemy_db.session.commit()
            print(f"\n✓ Base de datos actualizada: {migrated} registros de máquinas")
        except Exception as e:
            alchemy_db.session.rollback()
            print(f"\n✗ Error al guardar en base de datos: {e}")
            return 0, errors
    
    return migrated, errors

def main():
    print("=" * 60)
    print("Migración de imágenes '_migrated' a nombres consistentes")
    print("=" * 60)
    
    # Verificar directorios
    base_dir = os.path.abspath(os.path.dirname(__file__))
    perfiles_dir = os.path.join(base_dir, 'database', 'almacenamiento', 'perfiles')
    logos_dir = os.path.join(base_dir, 'database', 'almacenamiento', 'logos')
    
    os.makedirs(perfiles_dir, exist_ok=True)
    os.makedirs(logos_dir, exist_ok=True)
    
    print(f"\nDirectorio de perfiles: {perfiles_dir}")
    print(f"Directorio de logos: {logos_dir}")
    
    # Migrar perfiles
    print("\n" + "-" * 40)
    print("MIGRANDO IMÁGENES DE PERFIL")
    print("-" * 40)
    profiles_migrated, profile_errors = migrate_profile_images()
    
    # Migrar logos
    print("\n" + "-" * 40)
    print("MIGRANDO LOGOS DE MÁQUINAS")
    print("-" * 40)
    logos_migrated, logo_errors = migrate_machine_logos()
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE MIGRACIÓN")
    print("=" * 60)
    print(f"Perfiles migrados: {profiles_migrated}")
    print(f"Logos migrados: {logos_migrated}")
    print(f"Errores totales: {len(profile_errors) + len(logo_errors)}")
    
    if profile_errors or logo_errors:
        print("\nErrores encontrados:")
        for error in profile_errors + logo_errors:
            print(f"  - {error}")
    
    print("\n✓ Migración completada")
    return 0

if __name__ == "__main__":
    sys.exit(main())
