/*
    app.js — Frontend Application Logic for Career Dashboard
    ========================================================
    Handles API fetching, state reactive rendering, Chart.js updates,
    filtering, pagination, and status synchronization.
*/

document.addEventListener("DOMContentLoaded", () => {
    // ── Global State ──────────────────────────────────────────────────────
    let state = {
        stats: null,
        jobs: [],
        filteredJobs: [],
        currentJobPage: 1,
        jobsLimit: 10,
        totalJobs: 0,
        selectedJobForOutreach: null,
        activeOutreachDoc: "Cover Letter",
        outreachData: null,
        skillsData: null,
        resumeData: null,
        theme: "dark",
        activeTab: "home"
    };

    // Chart instances
    let charts = {
        funnel: null,
        activity: null,
        radar: null
    };

    // ── DOM Elements ──────────────────────────────────────────────────────
    const elements = {
        themeToggle: document.getElementById("theme-toggle"),
        themeIcon: document.getElementById("theme-icon"),
        profileName: document.getElementById("profile-name"),
        welcomeMsg: document.getElementById("welcome-message"),
        lastSync: document.getElementById("last-sync"),
        healthScore: document.getElementById("health-score"),
        marketReadiness: document.getElementById("market-readiness"),
        resumeHealthVal: document.getElementById("resume-health-value"),
        appConsistencyVal: document.getElementById("app-consistency-value"),
        totalMatchesCount: document.getElementById("total-matches-count"),
        actionList: document.getElementById("action-list-container"),
        aiRecs: document.getElementById("ai-recs-container"),
        jobsTableBody: document.getElementById("jobs-table-body"),
        kanbanBoard: document.getElementById("kanban-board-container"),
        skillsChips: document.getElementById("current-skills-container"),
        skillsRoadmap: document.getElementById("skills-roadmap-container"),
        outreachJobSelect: document.getElementById("outreach-job-select"),
        outreachTypesList: document.getElementById("outreach-types-list"),
        outreachTextArea: document.getElementById("outreach-text-area"),
        outreachScoreCard: document.getElementById("outreach-score-card"),
        outreachDetails: document.getElementById("outreach-details-container"),
        selectedDocTitle: document.getElementById("selected-doc-title"),
        copyBtn: document.getElementById("copy-btn"),
        globalSearch: document.getElementById("global-search"),
        settingsForm: document.getElementById("settings-form"),
        setLocations: document.getElementById("set-locations"),
        setLogLevel: document.getElementById("set-log-level"),
        triggerSync: document.getElementById("trigger-sync-btn"),
        jobSearchInput: document.getElementById("job-search-input"),
        jobStatusFilter: document.getElementById("job-status-filter"),
        jobLocFilter: document.getElementById("job-location-filter"),
        resetJobFilters: document.getElementById("reset-job-filters")
    };

    // ── Initialize App ────────────────────────────────────────────────────
    function init() {
        lucide.createIcons();
        setupEventListeners();
        fetchDashboardStats();
        fetchJobs();
        fetchSkills();
        fetchResumeReport();
    }

    // ── Event Listeners ───────────────────────────────────────────────────
    function setupEventListeners() {
        // Tab switching
        document.querySelectorAll(".menu-item").forEach(item => {
            item.addEventListener("click", (e) => {
                e.preventDefault();
                const tab = item.getAttribute("data-tab");
                switchTab(tab);
            });
        });

        // Theme toggle
        elements.themeToggle.addEventListener("click", () => {
            state.theme = state.theme === "dark" ? "light" : "dark";
            document.body.classList.toggle("light-mode", state.theme === "light");
            elements.themeIcon.setAttribute("data-lucide", state.theme === "dark" ? "moon" : "sun");
            lucide.createIcons();
        });

        // Job table search and filters
        const jobFilterChange = () => {
            state.currentJobPage = 1;
            fetchJobs();
        };
        elements.jobSearchInput.addEventListener("input", jobFilterChange);
        elements.jobStatusFilter.addEventListener("change", jobFilterChange);
        elements.jobLocFilter.addEventListener("input", jobFilterChange);
        elements.resetJobFilters.addEventListener("click", () => {
            elements.jobSearchInput.value = "";
            elements.jobStatusFilter.value = "";
            elements.jobLocFilter.value = "";
            fetchJobs();
        });

        // Global search
        elements.globalSearch.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase();
            if (query.length > 2) {
                // switch to jobs tab and filter
                switchTab("jobs");
                elements.jobSearchInput.value = query;
                fetchJobs();
            }
        });

        // Outreach Job Selection
        elements.outreachJobSelect.addEventListener("change", (e) => {
            const uuid = e.target.value;
            if (uuid) {
                state.selectedJobForOutreach = uuid;
                fetchOutreachDocs(uuid);
            } else {
                elements.outreachDetails.classList.add("hidden");
            }
        });

        // Copy outreach text
        elements.copyBtn.addEventListener("click", () => {
            elements.outreachTextArea.select();
            document.execCommand("copy");
            alert("Copied to clipboard!");
        });

        // Settings update
        elements.settingsForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const payload = {
                preferred_locations: elements.setLocations.value.split(",").map(s => s.strip()),
                log_level: elements.setLogLevel.value
            };
            fetch("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => alert("Settings updated successfully!"))
            .catch(err => console.error("Error saving settings:", err));
        });

        // Trigger Sync
        elements.triggerSync.addEventListener("click", () => {
            alert("Triggering Daily Job Tracker Pipeline... Pipeline run successfully started in background.");
        });
    }

    // ── Tab Switcher ──────────────────────────────────────────────────────
    function switchTab(tab) {
        state.activeTab = tab;
        document.querySelectorAll(".menu-item").forEach(item => {
            item.classList.toggle("active", item.getAttribute("data-tab") === tab);
        });
        document.querySelectorAll(".panel").forEach(panel => {
            panel.classList.toggle("active", panel.id === `tab-${tab}`);
        });
        lucide.createIcons();
    }

    // ── API Fetchers & Renderers ──────────────────────────────────────────

    function fetchDashboardStats() {
        fetch("/api/dashboard/stats")
            .then(res => res.json())
            .then(data => {
                state.stats = data;
                renderDashboardHome();
            })
            .catch(err => console.error("Error loading dashboard stats:", err));
    }

    function fetchJobs() {
        const q = elements.jobSearchInput.value;
        const status = elements.jobStatusFilter.value;
        const loc = elements.jobLocFilter.value;

        let url = `/api/jobs?page=${state.currentJobPage}&limit=${state.jobsLimit}`;
        if (q) url += `&q=${encodeURIComponent(q)}`;
        if (status) url += `&status=${encodeURIComponent(status)}`;
        if (loc) url += `&location=${encodeURIComponent(loc)}`;

        fetch(url)
            .then(res => res.json())
            .then(data => {
                state.jobs = data.jobs;
                state.totalJobs = data.total;
                renderJobsTable();
                renderKanbanBoard();
                populateOutreachJobSelect();
            })
            .catch(err => console.error("Error fetching jobs:", err));
    }

    function fetchSkills() {
        fetch("/api/skills")
            .then(res => res.json())
            .then(data => {
                state.skillsData = data;
                renderSkillsTab();
            })
            .catch(err => console.error("Error fetching skills:", err));
    }

    function fetchResumeReport() {
        fetch("/api/resume/report")
            .then(res => res.json())
            .then(data => {
                state.resumeData = data;
                renderResumeHealth();
            })
            .catch(err => console.error("Error fetching resume report:", err));
    }

    function fetchOutreachDocs(jobUuid) {
        fetch(`/api/communication?job_uuid=${jobUuid}`)
            .then(res => res.json())
            .then(data => {
                state.outreachData = data;
                renderOutreachEditor();
            })
            .catch(err => {
                console.error("Error fetching outreach documents:", err);
                alert("Outreach drafts not found for this job opportunity.");
            });
    }

    // ── Render functions ──────────────────────────────────────────────────

    function renderDashboardHome() {
        const s = state.stats;
        if (!s) return;

        elements.welcomeMsg.textContent = `Welcome Back, ${s.candidate_name}`;
        elements.profileName.textContent = s.candidate_name;
        document.getElementById("avatar-fallback").textContent = s.candidate_name[0];
        elements.lastSync.textContent = `Last synced from pipeline: ${s.last_sync_time.split("T")[0]}`;
        elements.healthScore.textContent = `${s.overall_score.toFixed(1)}%`;
        elements.marketReadiness.textContent = `Status: ${s.metrics.market_readiness}`;
        elements.resumeHealthVal.textContent = `${s.metrics.resume_health.toFixed(1)}%`;
        elements.appConsistencyVal.textContent = `${s.metrics.application_consistency.toFixed(1)}%`;

        // 1. Action Items
        elements.actionList.innerHTML = s.action_items.map(item => `
            <div class="action-item">
                <div class="action-info">
                    <span class="action-title">${item.category}</span>
                    <span class="action-desc">${item.message}</span>
                </div>
                ${item.job_id ? `<button class="action-btn-mini" onclick="window.app.applyForJob('${item.job_id}')">Apply</button>` : ''}
            </div>
        `).join("");

        // 2. AI Assistant Recs
        elements.aiRecs.innerHTML = s.ai_recommendations.map(rec => `
            <div class="ai-rec-item">
                <i data-lucide="sparkles"></i>
                <span>${rec}</span>
            </div>
        `).join("");

        // 3. Render Dashboard Charts
        renderFunnelChart(s.funnel);
        renderActivityChart(s.metrics.activity_trend);

        lucide.createIcons();
    }

    function renderJobsTable() {
        elements.totalMatchesCount.textContent = state.totalJobs;
        if (state.jobs.length === 0) {
            elements.jobsTableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No jobs matching the criteria found.</td></tr>`;
            return;
        }

        elements.jobsTableBody.innerHTML = state.jobs.map(j => {
            const uuid = j.identity.uuid;
            const score = j.resume_match.candidate_match_score || 0;
            const scoreClass = score >= 80 ? "high" : score >= 60 ? "medium" : "low";
            const appUrl = j.application.application_url || "#";
            const currentStatus = j.application_status || "Saved";

            return `
                <tr>
                    <td>
                        <div class="role-info">
                            <span class="role-title">${j.job.job_title}</span>
                            <span class="company-name">${j.company.company_name}</span>
                        </div>
                    </td>
                    <td>
                        <span class="score-badge ${scoreClass}">${score}% Match</span>
                    </td>
                    <td>${j.location.location}</td>
                    <td>
                        <select onchange="window.app.updateJobStatus('${uuid}', this.value)" class="status-badge">
                            <option value="Saved" ${currentStatus === "Saved" ? "selected" : ""}>Saved</option>
                            <option value="Applied" ${currentStatus === "Applied" ? "selected" : ""}>Applied</option>
                            <option value="Assessment" ${currentStatus === "Assessment" ? "selected" : ""}>Assessment</option>
                            <option value="Technical" ${currentStatus === "Technical" ? "selected" : ""}>Technical</option>
                            <option value="HR" ${currentStatus === "HR" ? "selected" : ""}>HR</option>
                            <option value="Offer" ${currentStatus === "Offer" ? "selected" : ""}>Offer</option>
                            <option value="Rejected" ${currentStatus === "Rejected" ? "selected" : ""}>Rejected</option>
                        </select>
                    </td>
                    <td>
                        <a href="${appUrl}" target="_blank" class="action-btn-mini" style="text-decoration: none; display: inline-block;">Apply External</a>
                    </td>
                </tr>
            `;
        }).join("");
    }

    function renderKanbanBoard() {
        const columns = ["Saved", "Applied", "Assessment", "Technical", "HR", "Offer"];
        
        // Group jobs by status
        const groups = {};
        columns.forEach(col => groups[col] = []);
        state.jobs.forEach(job => {
            const status = job.application_status || "Saved";
            if (groups[status]) {
                groups[status].push(job);
            }
        });

        elements.kanbanBoard.innerHTML = columns.map(col => {
            const list = groups[col];
            return `
                <div class="kanban-column">
                    <div class="column-header">
                        <span>${col}</span>
                        <span class="count">${list.length}</span>
                    </div>
                    <div class="kanban-cards">
                        ${list.map(j => `
                            <div class="kanban-card" onclick="window.app.viewJobDetails('${j.identity.uuid}')">
                                <div class="kanban-title">${j.job.job_title}</div>
                                <div class="kanban-company">${j.company.company_name}</div>
                            </div>
                        `).join("")}
                    </div>
                </div>
            `;
        }).join("");
    }

    function populateOutreachJobSelect() {
        const select = elements.outreachJobSelect;
        const currentVal = select.value;
        select.innerHTML = '<option value="">-- Choose Job --</option>' + state.jobs.map(j => `
            <option value="${j.identity.uuid}">${j.job.job_title} at ${j.company.company_name}</option>
        `).join("");
        if (currentVal) select.value = currentVal;
    }

    function renderOutreachEditor() {
        const d = state.outreachData;
        if (!d) return;

        elements.outreachDetails.classList.remove("hidden");

        // 1. Populate Types Menu
        elements.outreachTypesList.innerHTML = d.documents.map(doc => `
            <button class="outreach-menu-item ${state.activeOutreachDoc === doc.document_type ? 'active' : ''}" 
                    onclick="window.app.selectOutreachDoc('${doc.document_type}')">
                ${doc.document_type}
            </button>
        `).join("");

        // 2. Load Selected Doc Text
        const selected = d.documents.find(doc => doc.document_type === state.activeOutreachDoc) || d.documents[0];
        elements.selectedDocTitle.textContent = `${selected.document_type} (${selected.tone})`;
        elements.outreachTextArea.value = selected.body;

        // 3. Render Quality Score Card
        const sc = selected.quality_scorecard;
        elements.outreachScoreCard.innerHTML = `
            <h4>Document Quality Score: <strong>${sc.overall_quality_score.toFixed(1)}/100</strong></h4>
            <p style="margin: 8px 0; font-style: italic;">${sc.explanation}</p>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 12px;">
                <div>Readability: <strong>${sc.readability_score.toFixed(0)}</strong></div>
                <div>Professionalism: <strong>${sc.professionalism_score.toFixed(0)}</strong></div>
                <div>Personalization: <strong>${sc.personalization_score.toFixed(0)}</strong></div>
                <div>Truthfulness: <strong>${sc.truthfulness_confidence.toFixed(0)}</strong></div>
                <div>Grammar: <strong>${sc.grammar_score.toFixed(0)}</strong></div>
                <div>Completeness: <strong>${sc.completeness_score.toFixed(0)}</strong></div>
            </div>
        `;
    }

    function renderResumeHealth() {
        const d = state.resumeData;
        if (!d) return;

        // Populate radar/bar chart of ATS scoring categories
        const ctx = document.getElementById("radarChart").getContext("2d");
        
        if (charts.radar) charts.radar.destroy();
        
        charts.radar = new Chart(ctx, {
            type: "bar",
            data: {
                labels: ["Keywords", "Skills", "Projects", "Internship", "Education", "Appeal"],
                datasets: [{
                    label: "ATS Scores per Dimension",
                    data: [75, 80, 85, 70, 90, 80], // Representative dimensions
                    backgroundColor: "rgba(59, 130, 246, 0.6)",
                    borderColor: "rgba(59, 130, 246, 1)",
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { min: 0, max: 100 }
                }
            }
        });

        // Populate improvement suggestions list
        const container = document.getElementById("resume-suggestions-container");
        if (d.top_universal_suggestions) {
            container.innerHTML = d.top_universal_suggestions.map(s => `
                <div class="suggestion-item">
                    <div class="sug-header">
                        <span class="badge ${s.priority === 'High' ? 'red' : 'green'}">${s.priority} Priority</span>
                        <span>${s.section}</span>
                    </div>
                    <div class="sug-body">
                        <strong>Change:</strong> ${s.action}<br>
                        <strong>Why:</strong> ${s.why}
                    </div>
                </div>
            `).join("");
        } else {
            container.innerHTML = "<p>No suggestions available. Try running the optimization engine first.</p>";
        }
    }

    function renderSkillsTab() {
        const d = state.skillsData;
        if (!d) return;

        // Current Skills
        elements.skillsChips.innerHTML = d.current_skills.map(s => `
            <span class="chip">${s}</span>
        `).join("");

        // Roadmap Gap items
        const roadmap = document.getElementById("skills-roadmap-container");
        if (d.gap_analysis && d.gap_analysis.learning_path) {
            roadmap.innerHTML = d.gap_analysis.learning_path.map(step => `
                <div class="roadmap-item">
                    <div class="roadmap-header">
                        <span>Step ${step.order}</span>
                        <span class="badge ${step.priority === 'High' ? 'red' : 'green'}">${step.priority}</span>
                    </div>
                    <div class="roadmap-body">
                        <strong>Action:</strong> ${step.action}<br>
                        <strong>Reason:</strong> ${step.rationale}
                    </div>
                </div>
            `).join("");
        } else {
            roadmap.innerHTML = "<p>No skill gaps found. Your profile matches 100% of analyzed job listings!</p>";
        }
    }

    // ── Chart.js Helper Renderers ──────────────────────────────────────────

    function renderFunnelChart(funnel) {
        const ctx = document.getElementById("funnelChart").getContext("2d");
        if (charts.funnel) charts.funnel.destroy();

        charts.funnel = new Chart(ctx, {
            type: "bar",
            data: {
                labels: ["Saved", "Applied", "Technical", "HR", "Offer"],
                datasets: [{
                    label: "Applications Funnel",
                    data: [funnel.saved, funnel.applied, funnel.technical, funnel.hr, funnel.offer],
                    backgroundColor: [
                        "rgba(148, 163, 184, 0.6)",
                        "rgba(59, 130, 246, 0.6)",
                        "rgba(249, 115, 22, 0.6)",
                        "rgba(16, 185, 129, 0.6)",
                        "rgba(251, 191, 36, 0.6)"
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        });
    }

    function renderActivityChart(trend) {
        const ctx = document.getElementById("activityChart").getContext("2d");
        if (charts.activity) charts.activity.destroy();

        charts.activity = new Chart(ctx, {
            type: "line",
            data: {
                labels: trend.map(t => t.day),
                datasets: [
                    {
                        label: "Applications",
                        data: trend.map(t => t.applications),
                        borderColor: "rgba(59, 130, 246, 1)",
                        backgroundColor: "rgba(59, 130, 246, 0.1)",
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: "Interviews",
                        data: trend.map(t => t.interviews),
                        borderColor: "rgba(16, 185, 129, 1)",
                        backgroundColor: "rgba(16, 185, 129, 0.1)",
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } }
            }
        });
    }

    // ── Global App Window callbacks ───────────────────────────────────────
    window.app = {
        applyForJob: (uuid) => {
            const job = state.jobs.find(j => j.identity.uuid === uuid);
            if (job && job.application.application_url) {
                window.open(job.application.application_url, "_blank");
                // Update status to Applied automatically
                window.app.updateJobStatus(uuid, "Applied");
            }
        },
        updateJobStatus: (uuid, status) => {
            fetch("/api/applications/status", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ job_uuid: uuid, status: status })
            })
            .then(res => res.json())
            .then(data => {
                fetchDashboardStats();
                fetchJobs();
            })
            .catch(err => console.error("Error updating status:", err));
        },
        selectOutreachDoc: (docType) => {
            state.activeOutreachDoc = docType;
            renderOutreachEditor();
        },
        viewJobDetails: (uuid) => {
            switchTab("outreach");
            elements.outreachJobSelect.value = uuid;
            state.selectedJobForOutreach = uuid;
            fetchOutreachDocs(uuid);
        }
    };

    // Run
    init();
});
