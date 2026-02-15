import React, { useState, useEffect, createContext, useContext } from 'react'
import BunkerHeader from './BunkerHeader'
import BunkerFooter from './BunkerFooter'
import './BunkerLayout.css' // This will be scoped now

const BunkerSessionCtx = createContext({
    logged_in: false, nombre: null, is_guest: false, is_anonymous: false, is_admin: false,
    docker_logged_in: false, csrf_token: '', loaded: false, refresh: async () => { }
})

export function useBunkerSession() { return useContext(BunkerSessionCtx) }

export default function BunkerLayout({ children }) {
    const [sess, setSess] = useState({ logged_in: false, nombre: null, is_guest: false, is_anonymous: false, is_admin: false, docker_logged_in: false, csrf_token: '', loaded: false })

    const fetchSession = async () => {
        try {
            const r = await fetch('/bunkerlabs/api/session', { credentials: 'include' })
            const d = r.ok ? await r.json() : {}
            setSess(prev => ({ ...prev, ...d, loaded: true }))
            return d
        } catch {
            setSess(prev => ({ ...prev, loaded: true }))
            return null
        }
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
