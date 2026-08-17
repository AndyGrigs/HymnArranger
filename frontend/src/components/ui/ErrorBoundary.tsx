import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  /** Скинути помилку автоматично, коли це значення змінюється. */
  resetKey?: unknown
  label?: string
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidUpdate(prev: Props) {
    if (this.state.error && prev.resetKey !== this.props.resetKey) {
      this.setState({ error: null })
    }
  }

  reset = () => this.setState({ error: null })

  render() {
    const { error } = this.state
    if (!error) return this.props.children

    const label = this.props.label ?? 'Компонент'
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-ink/10 py-12 text-center">
        <p className="text-sm font-medium text-ink/60">{label} не вдалося відобразити</p>
        <p className="max-w-sm text-xs text-muted">{error.message}</p>
        <button
          type="button"
          onClick={this.reset}
          className="rounded border border-ink/15 px-3 py-1.5 text-xs text-muted transition hover:bg-ink/5 hover:text-ink"
        >
          Спробувати знову
        </button>
      </div>
    )
  }
}
