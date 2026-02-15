import React, { useState, useEffect, createContext, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import BunkerHeader from './BunkerHeader'
import BunkerFooter from './BunkerFooter'
import './BunkerLayout.css' // This will be scoped now

const BunkerSessionCtx = createContext({
    logged_in: false, nombre: null, is_guest: false, is_anonymous: false, is_admin: false,
    docker_logged_in: false, csrf_token: '', refresh: () => { }
})

export function useBunkerSession() { return useContext(BunkerSessionCtx) }

export default function BunkerLayout({ children }) {
    const [sess, setSess] = useState({ logged_in: false, nombre: null, is_guest: false, is_anonymous: false, is_admin: false, docker_logged_in: false, csrf_token: '' })
    const navigate = useNavigate()

    const fetchSession = () => {
        fetch('/bunkerlabs/api/session', { credentials: 'include' })
            .then(r => r.ok ? r.json() : {})
            .then(d => setSess(prev => ({ ...prev, ...d })))
            .catch(() => { })
    }

    useEffect(() => { fetchSession() }, [])

    const ctxValue = { ...sess, refresh: fetchSession }

    return (
        <BunkerSessionCtx.Provider value={ctxValue}>
            <div className="bunker-scope">
                <BunkerHeader />
                <main className="bunker-main-padding">
                    {children}
                </main>
                <BunkerFooter />
            </div>
        </BunkerSessionCtx.Provider>
    )
}
