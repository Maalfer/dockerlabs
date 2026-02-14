import React, { useEffect, useState } from 'react'
import RankingWriteupsModal from '../components/RankingWriteupsModal'
import RankingAutoresModal from '../components/RankingAutoresModal'
import AuthorProfileModal from '../components/AuthorProfileModal'
import WriteupModal from '../components/WriteupModal'
import MachineDescriptionModal from '../components/MachineDescriptionModal'
import './HomePage.css'

const ITEMS_PER_PAGE = 50

export default function HomePage() {
  const [maquinas, setMaquinas] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [filterDifficulty, setFilterDifficulty] = useState('todos')
  const [filterCategory, setFilterCategory] = useState('')
  const [filterCompleted, setFilterCompleted] = useState(null)
  const [showRankingWriteups, setShowRankingWriteups] = useState(false)
  const [showRankingAutores, setShowRankingAutores] = useState(false)
  const [authorProfileName, setAuthorProfileName] = useState(null)
  const [writeupModalMachine, setWriteupModalMachine] = useState(null)
  const [descriptionModal, setDescriptionModal] = useState(null)

  useEffect(() => {
    setLoading(true)
    fetch('/api/maquinas')
      .then(r => r.ok ? r.json() : [])
      .then(data => setMaquinas(data || []))
      .catch(() => setMaquinas([]))
      .finally(() => setLoading(false))
  }, [])

  const filtered = maquinas.filter(m => {
    const name = (m.nombre || '').toString().toLowerCase()
    const category = (m.categoria || '')
    const isCompleted = !!(m.completada || false)
    const difficultyClass = (m.clase) || 'todos'

    const matchSearch = name.includes(search.trim().toLowerCase())
    const matchDifficulty = filterDifficulty === 'todos' || difficultyClass === filterDifficulty
    const matchCategory = !filterCategory || category === filterCategory
    const matchCompleted = filterCompleted === null || (filterCompleted === true && isCompleted) || (filterCompleted === false && !isCompleted)

    return matchSearch && matchDifficulty && matchCategory && matchCompleted
  })

  // Counts per difficulty (mirror behavior of the original `updateAllButtonCounts`)
  const counts = React.useMemo(() => {
    const q = search.trim().toLowerCase()
    const map = { 'muy-facil': 0, 'facil': 0, 'medio': 0, 'dificil': 0, 'todos': 0 }
    maquinas.forEach(m => {
      const name = (m.nombre || '').toLowerCase()
      if (!name.includes(q)) return
      const cls = (m.clase || '').toLowerCase()
      if (cls && cls.indexOf('muy-facil') !== -1) map['muy-facil'] += 1
      else if (cls && cls.indexOf('facil') !== -1) map['facil'] += 1
      else if (cls && cls.indexOf('medio') !== -1) map['medio'] += 1
      else if (cls && cls.indexOf('dificil') !== -1) map['dificil'] += 1
      map['todos'] += 1
    })
    return map
  }, [maquinas, search])

  const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE))
  const pageItems = filtered.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)

  useEffect(() => { setCurrentPage(1) }, [search, filterDifficulty, filterCategory, filterCompleted])

  return (
    <div className="container">
      <div className="header row align-items-center" style={{ position: 'relative', zIndex: 1000 }}>
        <div className="col-12">
          <div className="header-filters-row">
            <div className="busqueda-con-filtro" style={{ maxWidth: 250 }}>
              <input type="text" id="buscador" className="form-control form-control-sm" placeholder="Busca algo." value={search} onChange={e => setSearch(e.target.value)} />
              <button className="btn dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false" title="Ordenar por fecha">
                <i className="bi bi-funnel"></i>
              </button>
              <ul className="dropdown-menu dropdown-menu-end">
                <li><a className="dropdown-item" href="#" onClick={(e) => { e.preventDefault(); /* sorting handled by server or additional logic */ }}>Fecha Reciente</a></li>
                <li><a className="dropdown-item" href="#" onClick={(e) => { e.preventDefault(); }}>Fecha Antiguos</a></li>
                <li><a className="dropdown-item" href="#" onClick={(e) => { e.preventDefault(); setFilterCompleted(true); }}>Máquinas Resueltas</a></li>
                <li><a className="dropdown-item" href="#" onClick={(e) => { e.preventDefault(); setFilterCompleted(false); }}>Máquinas Sin Resolver</a></li>
                <li><hr className="dropdown-divider" /></li>
                <li><a className="dropdown-item" href="#" onClick={(e) => { e.preventDefault(); setFilterCompleted(null); }}>Sin ordenar</a></li>
              </ul>

              <button className="btn btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false" title="Filtrar por categoría" style={{ border: 'none', transition: 'all 0.3s ease', right: 35 }}>
                <i className="bi bi-tags"></i>
              </button>
              <ul className="dropdown-menu dropdown-menu-end">
                <li><a className="dropdown-item" href="#" onClick={(e) => { e.preventDefault(); setFilterCategory(''); }}>Todas las categorías</a></li>
                <li><hr className="dropdown-divider" /></li>
                <li><a className="dropdown-item" href="#" onClick={(e) => { e.preventDefault(); setFilterCategory('Hacking Web'); }}>Hacking Web</a></li>
                <li><a className="dropdown-item" href="#" onClick={(e) => { e.preventDefault(); setFilterCategory('Bug Bounty'); }}>Bug Bounty</a></li>
                <li><a className="dropdown-item" href="#" onClick={(e) => { e.preventDefault(); setFilterCategory('Hacking CMS'); }}>Hacking CMS</a></li>
                <li><a className="dropdown-item" href="#" onClick={(e) => { e.preventDefault(); setFilterCategory('Hacking Infraestructura'); }}>Hacking Infraestructura</a></li>
                <li><a className="dropdown-item" href="#" onClick={(e) => { e.preventDefault(); setFilterCategory('Pivoting'); }}>Pivoting</a></li>
              </ul>
            </div>

            <button id="academia" className="btn btn-sm" onClick={() => window.open('https://elrincondelhacker.es', '_blank')}>Academia🧠</button>
            <button id="ranking" className="btn btn-sm" onClick={() => setShowRankingWriteups(true)}>Writeups👑</button>
            <button id="autores" className="btn btn-sm" onClick={() => setShowRankingAutores(true)}>Autores👑</button>
            <span className="filters-divider" aria-hidden="true"></span>

            <div className="d-flex flex-wrap gap-2 ms-auto" id="filtro-dificultad">
              <button id="boton-muy-facil" className={`btn btn-sm ${filterDifficulty === 'muy-facil' ? 'selected' : ''}`} onClick={() => { setFilterDifficulty('muy-facil'); setFilterCompleted(null); setCurrentPage(1); }}>Muy Fácil ({counts['muy-facil']})</button>
              <button id="boton-facil" className={`btn btn-sm ${filterDifficulty === 'facil' ? 'selected' : ''}`} onClick={() => { setFilterDifficulty('facil'); setFilterCompleted(null); setCurrentPage(1); }}>Fácil ({counts['facil']})</button>
              <button id="boton-medio" className={`btn btn-sm ${filterDifficulty === 'medio' ? 'selected' : ''}`} onClick={() => { setFilterDifficulty('medio'); setFilterCompleted(null); setCurrentPage(1); }}>Medio ({counts['medio']})</button>
              <button id="boton-dificil" className={`btn btn-sm ${filterDifficulty === 'dificil' ? 'selected' : ''}`} onClick={() => { setFilterDifficulty('dificil'); setFilterCompleted(null); setCurrentPage(1); }}>Difícil ({counts['dificil']})</button>
              <button id="boton-todos" className={`btn btn-sm ${filterDifficulty === 'todos' ? 'selected' : ''}`} onClick={() => { setFilterDifficulty('todos'); setFilterCompleted(null); setCurrentPage(1); }}>Todos ({counts['todos']})</button>
            </div>
          </div>
        </div>
      </div>

      {loading && <p style={{ marginTop: '2rem' }}>Cargando máquinas...</p>}

      <div className={"lista"} style={{ marginTop: '1rem' }}>
        {(!loading && pageItems.length === 0) && <p>No hay máquinas que mostrar.</p>}

        {pageItems.map((m, idx) => (
          <div key={m.id || idx}
            onClick={() => window.presentacion && window.presentacion(m.nombre, m.dificultad, m.color, m.autor, m.enlace_autor, m.fecha, m.imagen, m.categoria)}
            className={`maquina-item ${m.clase || ''}`} data-category={m.categoria || ''}>
            <span><strong>{m.nombre}</strong></span>
            <span className={`etiqueta ${m.clase || ''}`}>{m.dificultad}</span>
            <div className="acciones">
              <button className="btn-descripcion" style={{ fontSize: '0.9em' }} onClick={(e) => { e.stopPropagation(); setDescriptionModal({ name: m.nombre, description: m.descripcion }) }}>Descripción</button>
            </div>
            <div className="acciones">
              <button className="subir" style={{ fontSize: '1.2em' }} onClick={(e) => { e.stopPropagation(); window.open(m.link_descarga, '_blank') }} title="Descargar máquina"><i className="bi bi-cloud-arrow-down-fill"></i></button>
              <button className="subir" style={{ fontSize: '1.2em' }} onClick={(e) => { e.stopPropagation(); window.subirwriteup && window.subirwriteup(m.nombre) }} title="Subir writeup"><i className="bi bi-cloud-arrow-up-fill"></i></button>
              <button style={{ fontSize: '1.2em' }} onClick={(e) => { e.stopPropagation(); setWriteupModalMachine(m.nombre) }} title="Ver writeups"><i className="bi bi-book"></i></button>
            </div>
          </div>
        ))}
      </div>

      {/* Pagination container (scripts expect #pagination-container) */}
      <div className="header-pagination-row" style={{ marginTop: '2rem' }}>
        <div id="pagination-container" className="pagination-container" style={{ display: filtered.length > ITEMS_PER_PAGE ? 'block' : 'none' }}></div>
      </div>

      <RankingWriteupsModal
        open={showRankingWriteups}
        onClose={() => setShowRankingWriteups(false)}
        onOpenAuthor={(name) => { setShowRankingWriteups(false); setAuthorProfileName(name) }}
      />
      <RankingAutoresModal
        open={showRankingAutores}
        onClose={() => setShowRankingAutores(false)}
        onOpenAuthor={(name) => { setShowRankingAutores(false); setAuthorProfileName(name) }}
      />
      <AuthorProfileModal
        open={!!authorProfileName}
        authorName={authorProfileName}
        onClose={() => setAuthorProfileName(null)}
      />

      <WriteupModal
        machineName={writeupModalMachine}
        onClose={() => setWriteupModalMachine(null)}
      />

      <MachineDescriptionModal
        machineName={descriptionModal ? descriptionModal.name : null}
        description={descriptionModal ? descriptionModal.description : null}
        onClose={() => setDescriptionModal(null)}
      />
    </div>
  )
}
