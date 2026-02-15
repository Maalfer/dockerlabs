
@maquinas_bp.route('/api/public/maquinas', methods=['GET'])
# Public access - no @role_required
def api_get_public_maquinas():
    """
    Get public list of machines for Home Page (React).
    Includes 'completada' status for logged-in users.
    """
    current_username = (session.get('username') or '').strip()
    
    # 1. Fetch Machines
    maquinas_docker = Machine.query.filter_by(origen='docker').order_by(Machine.id.asc()).all()
    maquinas_bunker = Machine.query.filter_by(origen='bunker').order_by(Machine.id.asc()).all()
    
    # 2. Fetch Completed IDs if user is logged in
    completed_ids = set()
    if current_username:
        try:
            completes = CompletedMachine.query.filter_by(username=current_username).all()
            completed_ids = {c.machine_id for c in completes}
        except Exception:
            pass # Graceful fallback
            
    # 3. Fetch Categories
    # Optimization: Fetch all categories and map in memory
    # Or just fetch per machine (slow).
    # Better: Fetch all categories.
    cats = Category.query.all()
    cat_map = {(c.origen, c.machine_id): c.categoria for c in cats}
    
    def serialize_public(m):
        return {
            'id': m.id,
            'nombre': m.nombre,
            'dificultad': m.dificultad,
            'clase': m.clase, # Needed for styling
            'color': m.color,
            'autor': m.autor,
            'enlace_autor': m.enlace_autor,
            'fecha': m.fecha,
            'imagen': m.imagen,
            'descripcion': m.descripcion,
            'link_descarga': m.link_descarga,
            'guest_access': m.guest_access if hasattr(m, 'guest_access') else False,
            'origen': m.origen,
            'categoria': cat_map.get((m.origen, m.id), ''),
            'completada': m.id in completed_ids
        }

    return jsonify({
        'docker': [serialize_public(m) for m in maquinas_docker],
        'bunker': [serialize_public(m) for m in maquinas_bunker]
    }), 200
