// Expose minimal helper functions to mimic original behavior used by templates.
window.presentacion = function(nombre, dificultad, color, autor, enlace_autor, fecha, imagen, categoria) {
  const detail = { nombre, dificultad, color, autor, enlace_autor, fecha, imagen, categoria };
  window.dispatchEvent(new CustomEvent('open-machine-modal', { detail }));
}

window.descripcion = function(nombre, descripcion){
  alert('Descripción de ' + nombre + ':\n\n' + (descripcion || 'No hay descripción'))
}

window.subirwriteup = function(nombre){
  alert('Subir writeup para: ' + nombre)
}

window.showEnlaces = function(nombre){
  alert('Ver writeups de: ' + nombre)
}

// Ranking modals are now React components in HomePage; keep no-op for legacy script compatibility
window.ranking = function(){ /* opened via React state in HomePage */ }
window.rankingautores = function(){ /* opened via React state in HomePage */ }

// Difficulty filter helpers (kept for compatibility if scripts call them)
window.botonmuyfacil = function(){ document.getElementById('boton-muy-facil')?.click() }
window.botonfacil = function(){ document.getElementById('boton-facil')?.click() }
window.botonmedio = function(){ document.getElementById('boton-medio')?.click() }
window.botondificil = function(){ document.getElementById('boton-dificil')?.click() }
window.botontodos = function(){ document.getElementById('boton-todos')?.click() }

// Expose modal-opening functions used by legacy scripts by triggering the corresponding buttons
window.openMenuModal = function(){ document.getElementById('menu-button')?.click() }
window.openMessagingModal = function(){ document.getElementById('messaging-button')?.click() }
window.openGestionWriteupsModal = function(){ document.getElementById('gestion-button')?.click() }
window.openDashboardModal = function(){ document.getElementById('dashboard-button')?.click() }
