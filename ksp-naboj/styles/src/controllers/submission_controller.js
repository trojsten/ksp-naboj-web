import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
    static targets = ["button", "feedback", "result"]

    feedbackTimeout = null
    pollTimer = null

    connect() {
        this._boundOnSelect = this.onSelect.bind(this)
        window.addEventListener("problem:select", this._boundOnSelect)
    }

    disconnect() {
        window.removeEventListener("problem:select", this._boundOnSelect)
        if (this.feedbackTimeout) clearTimeout(this.feedbackTimeout)
        if (this.pollTimer) clearTimeout(this.pollTimer)
    }

    onSelect(event) {
        this.currentProblemId = event.detail.problemId
        this.hideFeedback()
    }

    async submit(event) {
        event.preventDefault()
        if (!this.currentProblemId) return

        const editorElement = document.querySelector(
            "[data-controller*='monaco-editor']"
        )
        const editorController =
            this.application.getControllerForElementAndIdentifier(
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
                    "X-CSRFToken":
                        document.querySelector('meta[name="csrf-token"]')
                            ?.content || "",
                },
                body: JSON.stringify({
                    problem_id: this.currentProblemId,
                    code,
                    language,
                }),
            })

            const result = await response.json()

            if (response.ok) {
                if (result.status === "pending" && result.judge_public_id) {
                    this.showFeedback(
                        "info",
                        "Submitted — waiting for result..."
                    )
                    this.buttonTarget.textContent = "Judging..."
                    this._pollStatus(result.judge_public_id)
                    return
                }
                this._showResult(result)
            } else {
                this.showFeedback(
                    "error",
                    result.error_message || result.error || "Submission failed"
                )
            }
        } catch {
            this.showFeedback("error", "Network error. Please try again.")
        } finally {
            if (!this.pollTimer) {
                this.buttonTarget.disabled = false
                this.buttonTarget.textContent = "Submit"
            }
        }
    }

    _pollStatus(publicId, attempt = 0) {
        const maxAttempts = 90 // ~3 min at 2s intervals
        this.pollTimer = setTimeout(async () => {
            try {
                const response = await fetch(
                    `/competition/status/${publicId}/`,
                    { headers: { "X-CSRFToken": document.querySelector('meta[name="csrf-token"]')?.content || "" } }
                )
                const result = await response.json()
                if (response.ok && result.status && result.status !== "pending") {
                    this.pollTimer = null
                    this._showResult(result)
                    this.buttonTarget.disabled = false
                    this.buttonTarget.textContent = "Submit"
                    return
                }
            } catch {
                // network hiccup — keep polling
            }
            if (attempt + 1 < maxAttempts) {
                this._pollStatus(publicId, attempt + 1)
            } else {
                this.pollTimer = null
                this.showFeedback(
                    "warning",
                    "Taking longer than expected. Your submission will update soon."
                )
                this.buttonTarget.disabled = false
                this.buttonTarget.textContent = "Submit"
            }
        }, 2000)
    }

    _showResult(result) {
        if (result.status === "accepted") {
            this.showFeedback(
                "success",
                result.execution_time != null
                    ? `Accepted! (${result.execution_time}s)`
                    : "Accepted!"
            )
        } else {
            const label = this._statusLabel(result.status)
            const message = result.error_message
                ? `${label}: ${result.error_message}`
                : label
            this.showFeedback("error", message)
        }
    }

    showFeedback(type, message) {
        if (this.feedbackTimeout) clearTimeout(this.feedbackTimeout)

        const colors = {
            success: "bg-success/10 text-success border-success/30",
            error: "bg-error/10 text-error border-error/30",
            warning: "bg-warning/10 text-warning border-warning/30",
            info: "bg-info/10 text-info border-info/30",
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
