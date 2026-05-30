import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
    select(event) {
        const button = event.currentTarget
        const problemId = button.dataset.problemId

        if (!problemId || button.disabled) return

        this.element.querySelectorAll(".problem-item").forEach((el) => {
            el.classList.remove("bg-primary/10")
        })
        button.classList.add("bg-primary/10")

        const pid = parseInt(problemId)

        window.dispatchEvent(
            new CustomEvent("problem:select", {
                detail: { problemId: pid },
            })
        )

        // Report activity to server (fire-and-forget)
        fetch("/competition/activity/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken":
                    document.querySelector('meta[name="csrf-token"]')
                        ?.content || "",
            },
            body: JSON.stringify({ problem_id: pid }),
        }).catch(() => {})
    }
}
