# Endpoints para gestión de writeups
@bunkerlabs_bp.route('/admin/writeups/add', methods=['POST'])
@role_required('admin')
@csrf_protect
@extensions.limiter.limit("10 per minute", methods=["POST"])
def add_writeup():
    """Añadir writeup para máquina de Entornos Reales."""
    from .models import BunkerWriteup
    
    maquina = (request.form.get('maquina') or '').strip()
    autor = (request.form.get('autor') or '').strip()
    url = (request.form.get('url') or '').strip()
    tipo = (request.form.get('tipo') or '').strip()
    
    if not all([maquina, autor, url, tipo]) or tipo not in ['texto', 'video']:
        flash('Todos los campos son obligatorios y el tipo debe ser texto o video.', 'error')
        return redirect(url_for('bunkerlabs.accesos_bunkerlabs'))
    
    try:
        new_writeup = BunkerWriteup(
            maquina=maquina,
            autor=autor,
            url=url,
            tipo=tipo
        )
        alchemy_db.session.add(new_writeup)
        alchemy_db.session.commit()
        flash(f'Writeup añadido correctamente para {maquina}', 'success')
    except IntegrityError:
        alchemy_db.session.rollback()
        flash('Error: Este writeup ya existe.', 'error')
    except Exception as e:
        alchemy_db.session.rollback()
        flash(f'Error al añadir writeup: {str(e)}', 'error')
    
    return redirect(url_for('bunkerlabs.accesos_bunkerlabs'))

@bunkerlabs_bp.route('/admin/writeups/delete/<int:writeup_id>', methods=['POST'])
@role_required('admin')
@csrf_protect
@extensions.limiter.limit("10 per minute", methods=["POST"])
def delete_writeup(writeup_id):
    """Eliminar writeup."""
    from .models import BunkerWriteup
    
    writeup = BunkerWriteup.query.get(writeup_id)
    
    if not writeup:
        flash('Writeup no encontrado.', 'error')
        return redirect(url_for('bunkerlabs.accesos_bunkerlabs'))
    
    try:
        alchemy_db.session.delete(writeup)
        alchemy_db.session.commit()
        flash('Writeup eliminado correctamente.', 'success')
    except Exception as e:
        alchemy_db.session.rollback()
        flash(f'Error al eliminar writeup: {str(e)}', 'error')
    
    return redirect(url_for('bunkerlabs.accesos_bunkerlabs'))
