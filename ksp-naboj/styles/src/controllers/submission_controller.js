import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
    static targets = ["button", "feedback", "result"]
    static values = {
        teamId: String,
    }

    feedbackTimeout = null

    connect() {
        this._boundOnSelect = this.onSelect.bind(this)
        window.addEventListener("problem:select", this._boundOnSelect)
    }

    disconnect() {
        window.removeEventListener("problem:select", this._boundOnSelect)
        if (this.feedbackTimeout) clearTimeout(this.feedbackTimeout)
    }

    onSelect(event) {
        this.currentProblemId = event.detail.problemId
        this.hideFeedback()
    }

    async submit(event) {
        event.preventDefault()
        if (!this.currentProblemId) return

        const editorElement = document.querySelector("[data-controller*='monaco-editor']")
        const editorController = this.application.getControllerForElementAndIdentifier(
            editorElement,
            "monaco-editor"
        )
        if (!editorController) return

        const code = editorController.getCode()
        const language = editorController.getLanguage()

        if (!code.trim()) {
            this.showFeedback("warning", "Cannot submit empty code.")
            return
        }

        this.buttonTarget.disabled = true
        this.buttonTarget.textContent = "Submitting..."

        try {
            const response = await fetch("/competition/submit/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": document.querySelector(
                        'meta[name="csrf-token"]'
                    )?.content || document.querySelector('[name="csrfmiddlewaretoken"]')?.value,
                },
                body: JSON.stringify({
                    problem_id: this.currentProblemId,
                    code,
                    language,
                    team_id: this.teamIdValue,
                }),
            })

            const result = await response.json()

            if (response.ok) {
                if (result.status === "accepted") {
                    this.showFeedback(
                        "success",
                        `Accepted! (${result.execution_time}s)`
                    )
                    window.dispatchEvent(
                        new CustomEvent("submission:accepted", {
                            detail: { problemId: this.currentProblemId },
                        })
                    )
                } else {
                    this.showFeedback(
                        "error",
                        `${this._statusLabel(result.status)}: ${result.error_message}`
                    )
                }
            } else {
                this.showFeedback("error", result.error || "Submission failed")
            }
        } catch (err) {
            this.showFeedback("error", "Network error. Please try again.")
        } finally {
            this.buttonTarget.disabled = false
            this.buttonTarget.textContent = "Submit"
        }
    }

    showFeedback(type, message) {
        if (this.feedbackTimeout) clearTimeout(this.feedbackTimeout)

        const colors = {
            success: "bg-success/10 text-success border-success/30",
            error: "bg-error/10 text-error border-error/30",
            warning: "bg-warning/10 text-warning border-warning/30",
        }

        this.feedbackTarget.className = `px-3 py-2 rounded text-sm border ${colors[type] || colors.error}`
        this.resultTarget.textContent = message
        this.feedbackTarget.classList.remove("hidden")

        this.feedbackTimeout = setTimeout(() => this.hideFeedback(), 8000)
    }

    hideFeedback() {
        this.feedbackTarget.classList.add("hidden")
    }

    _statusLabel(status) {
        const labels = {
            rejected: "Wrong Answer",
            runtime_error: "Runtime Error",
            compilation_error: "Compilation Error",
            time_limit_exceeded: "Time Limit Exceeded",
            memory_limit_exceeded: "Memory Limit Exceeded",
        }
        return labels[status] || status
    }
}
