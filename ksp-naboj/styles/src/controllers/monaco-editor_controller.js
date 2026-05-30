import { Controller } from "@hotwired/stimulus"
import * as monaco from "monaco-editor"

export default class extends Controller {
    static targets = ["container", "placeholder"]
    static values = {
        workerUrl: String,
        teamId: String,
    }

    currentProblemId = null
    editor = null
    _saveTimer = null

    // --- localStorage helpers ---

    _storageKey(problemId) {
        return `naboj:code:${this.teamIdValue}:${problemId}`
    }

    _loadCode(problemId) {
        try {
            return localStorage.getItem(this._storageKey(problemId)) || ""
        } catch {
            return ""
        }
    }

    _persistCode(problemId, code) {
        try {
            localStorage.setItem(this._storageKey(problemId), code)
        } catch {
            // localStorage full or unavailable
        }
    }

    // --- Stimulus lifecycle ---

    connect() {
        const dataEl = document.getElementById("problems-data")
        this.problems = dataEl ? JSON.parse(dataEl.textContent) : {}

        this._boundOnSelect = this.onSelect.bind(this)
        window.addEventListener("problem:select", this._boundOnSelect)

        // Re-parse problems data when htmx swaps in new data (OOB swap)
        this._boundOnSwap = () => {
            const el = document.getElementById("problems-data")
            if (el) this.problems = JSON.parse(el.textContent)
        }
        document.body.addEventListener("htmx:oobAfterSwap", this._boundOnSwap)
    }

    disconnect() {
        window.removeEventListener("problem:select", this._boundOnSelect)
        document.body.removeEventListener("htmx:oobAfterSwap", this._boundOnSwap)
        this._flushSave()
        this.editor?.dispose()
    }

    // --- Problem selection ---

    onSelect(event) {
        const { problemId } = event.detail
        const problem = this.problems[problemId]
        if (!problem) return

        this._flushSave()
        this.currentProblemId = problemId

        const lang = problem.language || "python"

        this.placeholderTarget.classList.add("hidden")
        this.containerTarget.classList.remove("hidden")

        if (this.editor) {
            const model = this.editor.getModel()
            monaco.editor.setModelLanguage(model, lang)
            this.editor.setValue(this._loadCode(problemId))
            this.editor.layout()
        } else {
            this._createEditor(lang)
        }

        const langLabel = document.getElementById("current-language")
        if (langLabel) langLabel.textContent = this._languageDisplayName(lang)
    }

    // --- Editor creation ---

    _createEditor(language) {
        self.MonacoEnvironment = {
            getWorkerUrl: () => this.workerUrlValue,
        }

        requestAnimationFrame(() => {
            this.editor = monaco.editor.create(this.containerTarget, {
                value: this._loadCode(this.currentProblemId),
                language,
                theme: "vs-dark",
                automaticLayout: true,
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                padding: { top: 12 },
            })

            // Auto-save on every change (debounced 500ms)
            this.editor.onDidChangeModelContent(() => {
                this._debouncedSave()
            })
        })
    }

    // --- Debounced save ---

    _debouncedSave() {
        if (this._saveTimer) clearTimeout(this._saveTimer)
        this._saveTimer = setTimeout(() => {
            if (this.editor && this.currentProblemId) {
                this._persistCode(this.currentProblemId, this.editor.getValue())
            }
        }, 500)
    }

    _flushSave() {
        if (this._saveTimer) {
            clearTimeout(this._saveTimer)
            this._saveTimer = null
        }
        if (this.editor && this.currentProblemId) {
            this._persistCode(this.currentProblemId, this.editor.getValue())
        }
    }

    // --- Public API (used by submission controller) ---

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
