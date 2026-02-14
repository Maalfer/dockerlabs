import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './styles.css'
import './client_helpers'

class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null } }
  static getDerivedStateFromError(error) { return { error } }
  componentDidCatch(error, info) { console.error('React crash:', error, info) }
  render() {
    if (this.state.error) return (
      <div style={{ padding: '2rem', color: '#ef4444', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
        <h2>Error de React</h2>
        <p>{this.state.error.toString()}</p>
        <p>{this.state.error.stack}</p>
      </div>
    )
    return this.props.children
  }
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </BrowserRouter>
  </React.StrictMode>
)
