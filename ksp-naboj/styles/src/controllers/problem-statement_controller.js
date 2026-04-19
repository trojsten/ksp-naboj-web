import { Controller } from "@hotwired/stimulus"
import { marked } from "marked"

export default class extends Controller {
    static targets = ["placeholder", "content", "title", "badge", "description"]

    connect() {
        const dataEl = document.getElementById("problems-data")
        this.problems = dataEl ? JSON.parse(dataEl.textContent) : {}
        this._boundOnSelect = this.onSelect.bind(this)
        window.addEventListener("problem:select", this._boundOnSelect)
    }

    disconnect() {
        window.removeEventListener("problem:select", this._boundOnSelect)
    }

    onSelect(event) {
        const { problemId } = event.detail
        const problem = this.problems[problemId]
        if (!problem) return

        this.titleTarget.textContent = problem.title

        this.badgeTarget.textContent = problem.difficulty === "easy" ? "Easy" : "Hard"
        this.badgeTarget.className = problem.difficulty === "easy"
            ? "text-xs rounded px-1.5 py-0.5 bg-success/10 text-success font-medium"
            : "text-xs rounded px-1.5 py-0.5 bg-error/10 text-error font-medium"

        this.descriptionTarget.innerHTML = marked.parse(problem.description)

        this.placeholderTarget.classList.add("hidden")
        this.contentTarget.classList.remove("hidden")
    }
}
