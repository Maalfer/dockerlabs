import React, { useEffect, useState, useMemo } from 'react'

const ITEMS_PER_PAGE = 50

export default function Home(){
  const [maquinas, setMaquinas] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [filter, setFilter] = useState({ difficulty: 'todos', category: '', completed: null })

  useEffect(()=>{
    setLoading(true)
    fetch('/api/maquinas')
      .then(r=> r.ok ? r.json() : [])
      .then(data => setMaquinas(data || []))
      .catch(()=> setMaquinas([]))
      .finally(()=> setLoading(false))
  },[])

  const normalizedSearch = search.trim().toLowerCase()

  const filtered = useMemo(()=>{
    return maquinas.filter(m => {
      const name = (m.nombre || '').toString().toLowerCase()
      const category = (m.categoria || '')
      const isCompleted = !!(m.completada || false) // backend can supply this later
      const difficultyClass = (m.clase) || 'todos'

      const matchSearch = name.includes(normalizedSearch)
      const matchDifficulty = filter.difficulty === 'todos' || difficultyClass === filter.difficulty
      const matchCategory = !filter.category || category === filter.category
      const matchCompleted = filter.completed === null || (filter.completed === true && isCompleted) || (filter.completed === false && !isCompleted)

      return matchSearch && matchDifficulty && matchCategory && matchCompleted
    })
  }, [maquinas, normalizedSearch, filter])

  const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE))
  const pageItems = filtered.slice((currentPage-1)*ITEMS_PER_PAGE, currentPage*ITEMS_PER_PAGE)

  useEffect(()=>{
    setCurrentPage(1)
  }, [search, filter])

  function updateDifficulty(buttonId, difficultyClass){
    setFilter({ difficulty: difficultyClass, category: '', completed: null })
  }

  function filterByCompleted(){ setFilter({ difficulty: 'todos', category: '', completed: true }) }
  function filterByUncompleted(){ setFilter({ difficulty: 'todos', category: '', completed: false }) }

  return (
    <div className="container">
      <div className="header row align-items-center" style={{position:'relative', zIndex:1000}}>
        <div className="col-12">
          <div className="header-filters-row d-flex align-items-center">
            <div className="busqueda-con-filtro" style={{maxWidth:250}}>
              <input value={search} onChange={e=>setSearch(e.target.value)} type="text" id="buscador" className="form-control form-control-sm" placeholder="Busca algo." />
            </div>

            <div className="d-flex flex-wrap gap-2 ms-auto" id="filtro-dificultad">
              <button id="boton-muy-facil" className={`btn btn-sm ${filter.difficulty==='muy-facil' ? 'selected':''}`} onClick={()=>updateDifficulty('boton-muy-facil','muy-facil')}>Muy Fácil</button>
              <button id="boton-facil" className={`btn btn-sm ${filter.difficulty==='facil' ? 'selected':''}`} onClick={()=>updateDifficulty('boton-facil','facil')}>Fácil</button>
              <button id="boton-medio" className={`btn btn-sm ${filter.difficulty==='medio' ? 'selected':''}`} onClick={()=>updateDifficulty('boton-medio','medio')}>Medio</button>
              <button id="boton-dificil" className={`btn btn-sm ${filter.difficulty==='dificil' ? 'selected':''}`} onClick={()=>updateDifficulty('boton-dificil','dificil')}>Difícil</button>
              <button id="boton-todos" className={`btn btn-sm ${filter.difficulty==='todos' ? 'selected':''}`} onClick={()=>updateDifficulty('boton-todos','todos')}>Todos</button>
            </div>
          </div>
        </div>
      </div>

      <div style={{marginTop:'1.5rem'}}>
        {loading && <p>Cargando máquinas...</p>}
        {!loading && pageItems.length === 0 && <p>No hay máquinas que mostrar.</p>}

        <div className="lista">
          {pageItems.map((m, idx)=> (
            <div key={m.id || idx} className={`maquina-item ${m.clase || ''}`} data-category={m.categoria || ''} onClick={()=> window.presentacion && window.presentacion(m.nombre, m.dificultad, m.color, m.autor, m.enlace_autor, m.fecha, m.imagen, m.categoria)}>
              <span><strong>{m.nombre}</strong>{m.is_new && <span className="etiqueta-nueva">¡Nueva!</span>}</span>
              <span className={`etiqueta ${m.clase || ''}`}>{m.dificultad}</span>
              <div className="acciones">
                <button className="btn-descripcion" style={{fontSize:'0.9em'}} onClick={(e)=>{ e.stopPropagation(); window.descripcion && window.descripcion(m.nombre, m.descripcion) }}>Descripción</button>
              </div>
              <div className="acciones">
                <button className="subir" style={{fontSize:'1.2em'}} onClick={(e)=>{ e.stopPropagation(); window.open(m.link_descarga, '_blank')}} title="Descargar máquina"><i className="bi bi-cloud-arrow-down-fill"></i></button>
                <button className="subir" style={{fontSize:'1.2em'}} onClick={(e)=>{ e.stopPropagation(); window.subirwriteup && window.subirwriteup(m.nombre)}} title="Subir writeup"><i className="bi bi-cloud-arrow-up-fill"></i></button>
                <button style={{fontSize:'1.2em'}} onClick={(e)=>{ e.stopPropagation(); window.showEnlaces && window.showEnlaces(m.nombre)}} title="Ver writeups"><i className="bi bi-book"></i></button>
              </div>
            </div>
          ))}
        </div>

        {/* Pagination */}
        <div style={{marginTop:'1rem', display: filtered.length > ITEMS_PER_PAGE ? 'flex' : 'none', justifyContent:'center'}}>
          <div className="pagination-wrapper">
            <button className="pagination-btn" disabled={currentPage<=1} onClick={()=>setCurrentPage(p=>Math.max(1,p-1))}>&laquo; Anterior</button>
            <span style={{margin:'0 8px'}}>{(currentPage-1)*ITEMS_PER_PAGE+1}-{Math.min(currentPage*ITEMS_PER_PAGE, filtered.length)} de {filtered.length}</span>
            {[...Array(Math.min(5, totalPages)).keys()].map(i => {
              const page = Math.min(Math.max(1, currentPage - 2 + i), totalPages)
              return <button key={page} className={`pagination-btn ${page===currentPage ? 'active':''}`} onClick={()=>setCurrentPage(page)}>{page}</button>
            })}
            <button className="pagination-btn" disabled={currentPage>=totalPages} onClick={()=>setCurrentPage(p=>Math.min(totalPages,p+1))}>Siguiente &raquo;</button>
          </div>
        </div>
      </div>
    </div>
  )
}
