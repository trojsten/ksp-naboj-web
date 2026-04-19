import { Controller } from "@hotwired/stimulus"
import * as monaco from "monaco-editor"

export default class extends Controller {
    static targets = ["container", "placeholder"]
    static values = {
        workerUrl: String,
    }

    codeStore = new Map()
    currentProblemId = null
    editor = null

    connect() {
        const dataEl = document.getElementById("problems-data")
        this.problems = dataEl ? JSON.parse(dataEl.textContent) : {}
        this._boundOnSelect = this.onSelect.bind(this)
        window.addEventListener("problem:select", this._boundOnSelect)
    }

    disconnect() {
        window.removeEventListener("problem:select", this._boundOnSelect)
        this.editor?.dispose()
    }

    onSelect(event) {
        const { problemId } = event.detail
        const problem = this.problems[problemId]
        if (!problem) return

        this._saveCurrentCode()
        this.currentProblemId = problemId

        const lang = problem.language || "python"

        this.placeholderTarget.classList.add("hidden")
        this.containerTarget.classList.remove("hidden")

        if (this.editor) {
            const model = this.editor.getModel()
            monaco.editor.setModelLanguage(model, lang)
            this.editor.setValue(this.codeStore.get(problemId) || "")
            this.editor.layout()
        } else {
            this._createEditor(lang)
        }

        const langLabel = document.getElementById("current-language")
        if (langLabel) langLabel.textContent = this._languageDisplayName(lang)
    }

    _createEditor(language) {
        self.MonacoEnvironment = {
            getWorkerUrl: () => this.workerUrlValue,
        }

        requestAnimationFrame(() => {
            this.editor = monaco.editor.create(this.containerTarget, {
                value: this.codeStore.get(this.currentProblemId) || "",
                language,
                theme: "vs-dark",
                automaticLayout: true,
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                padding: { top: 12 },
            })
        })
    }

    _saveCurrentCode() {
        if (this.editor && this.currentProblemId) {
            this.codeStore.set(this.currentProblemId, this.editor.getValue())
        }
    }

    getCode() {
        return this.editor?.getValue() || ""
    }

    getLanguage() {
        const model = this.editor?.getModel()
        return model ? model.getLanguageId() : ""
    }

    _languageDisplayName(langId) {
        const names = {
            python: "Python",
            cpp: "C++",
            c: "C",
            java: "Java",
            javascript: "JavaScript",
            typescript: "TypeScript",
            rust: "Rust",
            go: "Go",
        }
        return names[langId] || langId
    }
}
