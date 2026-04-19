import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
    static targets = ["item"]

    select(event) {
        const button = event.currentTarget
        const problemId = button.dataset.problemId

        if (!problemId || button.disabled) return

        this.element.querySelectorAll(".problem-item").forEach((el) => {
            el.classList.remove("bg-primary/10")
        })
        button.classList.add("bg-primary/10")

        window.dispatchEvent(
            new CustomEvent("problem:select", {
                detail: { problemId: parseInt(problemId) },
            })
        )
    }
}
