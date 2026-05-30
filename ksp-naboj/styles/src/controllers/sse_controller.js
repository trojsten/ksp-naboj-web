import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
    static values = {
        url: String,
    }

    connect() {
        this._connect()
    }

    disconnect() {
        this._close()
    }

    _connect() {
        this.eventSource = new EventSource(this.urlValue)

        this.eventSource.addEventListener("problem-list", (event) => {
            const container = document.getElementById("problem-list-container")
            if (container) {
                // Preserve the currently selected problem highlight
                const selected = container.querySelector(".bg-primary\\/10")
                const selectedId = selected?.dataset?.problemId

                container.innerHTML = event.data

                // Re-apply selection highlight
                if (selectedId) {
                    const btn = container.querySelector(
                        `[data-problem-id="${selectedId}"]`
                    )
                    if (btn) btn.classList.add("bg-primary/10")
                }
            }
        })

        this.eventSource.addEventListener("problems-json", (event) => {
            const el = document.getElementById("problems-data")
            if (el) {
                el.textContent = event.data
                // Notify controllers to re-parse
                document.body.dispatchEvent(
                    new CustomEvent("htmx:oobAfterSwap")
                )
            }
        })

        this.eventSource.onerror = () => {
            // Reconnect after a delay on error
            this._close()
            setTimeout(() => this._connect(), 5000)
        }
    }

    _close() {
        if (this.eventSource) {
            this.eventSource.close()
            this.eventSource = null
        }
    }
}
