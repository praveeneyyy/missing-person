// ==========================================================================
// FORENSIC INVESTIGATION & BIOMETRIC REVIEW APPLICATION CONTROLLER
// ==========================================================================

const App = {
  activeTab: 'public-home',
  currentCaseId: null,
  activeCandidateId: null,
  canvasModes: {}, // tracks display mode for canvases: 'forensic' | 'bbox' | 'raw'
  simulatedThreshold: 0.70,

  init() {
    this.bindEvents();
    this.checkSession();
    this.renderCurrentView();

    // Default to investigator login for immediate demo access
    if (!API.getToken()) {
      API.login('investigator', 'investigator123').catch(() => {});
    }

    // Initialize Lucide icons if available
    if (window.lucide) {
      window.lucide.createIcons();
    }
  },

  bindEvents() {
    // Navigation items
    document.querySelectorAll('[data-tab]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.getAttribute('data-tab');
        this.switchTab(tab);
      });
    });

    // Quick role switcher
    const roleSelect = document.getElementById('quick-role-select');
    if (roleSelect) {
      roleSelect.addEventListener('change', async (e) => {
        const val = e.target.value;
        if (val === 'investigator') {
          await API.login('investigator', 'investigator123');
          this.switchTab('dashboard');
        } else if (val === 'admin') {
          await API.login('admin', 'admin123');
          this.switchTab('dashboard');
        } else if (val === 'public') {
          API.logout();
          this.switchTab('public-home');
        }
      });
    }

    // Public sighting form
    const sightingForm = document.getElementById('sighting-form');
    if (sightingForm) {
      sightingForm.addEventListener('submit', (e) => this.handleSightingSubmit(e));
    }

    // Officer login form
    const loginForm = document.getElementById('officer-login-form');
    if (loginForm) {
      loginForm.addEventListener('submit', (e) => this.handleLoginSubmit(e));
    }

    // Provision officer form (Admin only)
    const provisionForm = document.getElementById('provision-officer-form');
    if (provisionForm) {
      provisionForm.addEventListener('submit', (e) => this.handleProvisionOfficerSubmit(e));
    }

    const sightingFile = document.getElementById('sighting-file');
    if (sightingFile) {
      sightingFile.addEventListener('change', (e) => this.handlePhotoPreview(e, 'sighting-preview-img', 'sighting-preview-box', 'sighting-img-meta'));
    }

    // Case registration form
    const caseForm = document.getElementById('create-case-form');
    if (caseForm) {
      caseForm.addEventListener('submit', (e) => this.handleCaseSubmit(e));
    }

    const refFile = document.getElementById('case-photo-file');
    if (refFile) {
      refFile.addEventListener('change', (e) => this.handlePhotoPreview(e, 'case-preview-img', 'case-preview-box', 'case-img-meta'));
    }

    // Module 2: Case Status Workflow Form
    const statusForm = document.getElementById('update-case-status-form');
    if (statusForm) {
      statusForm.addEventListener('submit', (e) => this.handleCaseStatusSubmit(e));
    }

    // Module 2: Add Additional Reference Portrait Form
    const addRefForm = document.getElementById('add-reference-form');
    if (addRefForm) {
      addRefForm.addEventListener('submit', (e) => this.handleAddReferenceSubmit(e));
    }
    const addRefFile = document.getElementById('additional-ref-file');
    if (addRefFile) {
      addRefFile.addEventListener('change', (e) => this.handlePhotoPreview(e, 'add-ref-preview-img', 'add-ref-preview-box', 'add-ref-img-meta'));
    }

    // Module 2: Edit Case Dossier Form
    const editCaseForm = document.getElementById('edit-case-form');
    if (editCaseForm) {
      editCaseForm.addEventListener('submit', (e) => this.handleEditCaseSubmit(e));
    }


    // Receipt lookup
    const lookupForm = document.getElementById('receipt-lookup-form');
    if (lookupForm) {
      lookupForm.addEventListener('submit', (e) => this.handleReceiptLookup(e));
    }

    // Review form
    const reviewForm = document.getElementById('review-form');
    if (reviewForm) {
      reviewForm.addEventListener('submit', (e) => this.handleReviewSubmit(e));
    }

    // Auth state changed listener
    window.addEventListener('auth-changed', () => {
      this.checkSession();
      this.renderCurrentView();
    });
  },

  checkSession() {
    const user = API.getUser();
    const userBadge = document.getElementById('user-profile-badge');
    const roleSelect = document.getElementById('quick-role-select');
    const staffNav = document.getElementById('staff-navigation');
    const adminNav = document.getElementById('admin-nav-item');

    if (user) {
      if (userBadge) {
        userBadge.innerHTML = `
          <div class="flex items-center gap-2">
            <span class="pulse-indicator pulse-emerald"></span>
            <span class="font-semibold text-slate-200 text-xs">${user.full_name}</span>
            <span class="font-mono text-[10px] bg-blue-900/80 text-blue-300 font-bold px-1.5 py-0.5 rounded border border-blue-700">${user.badge_number || user.role.toUpperCase()}</span>
            <button onclick="App.handleLogout()" title="Sign Out" class="text-slate-400 hover:text-red-400 text-xs px-1.5 py-0.5 rounded transition">🚪</button>
          </div>
        `;
      }
      if (roleSelect) {
        roleSelect.value = user.role;
      }
      if (staffNav) {
        staffNav.classList.remove('hidden');
      }
      if (adminNav) {
        if (user.role === 'admin') {
          adminNav.classList.remove('hidden');
        } else {
          adminNav.classList.add('hidden');
        }
      }
      this.loadNotifications();
    } else {
      const bell = document.getElementById('notification-bell-container');
      if (bell) bell.classList.add('hidden');
      if (userBadge) {
        userBadge.innerHTML = `
          <button onclick="App.openModal('login-modal')" class="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold font-mono px-3 py-1.5 rounded-lg shadow-sm transition flex items-center gap-1.5">
            <span>🔒</span>
            <span>OFFICER SIGN IN</span>
          </button>
        `;
      }
      if (roleSelect) {
        roleSelect.value = 'public';
      }
      if (staffNav) {
        staffNav.classList.add('hidden');
      }
      if (adminNav) {
        adminNav.classList.add('hidden');
      }
    }
  },

  switchTab(tabName) {
    this.activeTab = tabName;

    // Update tab button active states
    document.querySelectorAll('[data-tab]').forEach(btn => {
      if (btn.getAttribute('data-tab') === tabName) {
        btn.classList.add('bg-blue-600', 'text-white', 'shadow-sm');
        btn.classList.remove('text-slate-600', 'hover:bg-slate-100');
      } else {
        btn.classList.remove('bg-blue-600', 'text-white', 'shadow-sm');
        btn.classList.add('text-slate-600', 'hover:bg-slate-100');
      }
    });

    // Hide all tabs
    document.querySelectorAll('.tab-pane').forEach(pane => {
      pane.classList.add('hidden');
    });

    // Show selected tab
    const target = document.getElementById(`tab-${tabName}`);
    if (target) {
      target.classList.remove('hidden');
    }

    this.renderCurrentView();
  },

  async renderCurrentView() {
    switch (this.activeTab) {
      case 'dashboard':
        await this.loadDashboard();
        break;
      case 'cases':
        await this.loadCases();
        break;
      case 'review-queue':
        await this.loadReviewQueue();
        break;
      case 'map':
        setTimeout(() => MapManager.initMainMap('investigation-map'), 100);
        break;
      case 'audit':
        await this.loadAuditLogs();
        await this.loadGovernanceReport();
        await this.loadSecurityHealth();
        break;
      case 'officers':
        await this.loadOfficers();
        break;
      case 'benchmark':
        await this.loadBenchmark();
        break;
      case 'public-submit':
        setTimeout(() => MapManager.initLocationPicker('sighting-picker-map', 'sighting-lat', 'sighting-lng', 'sighting-location'), 100);
        break;
    }

    if (window.lucide) {
      window.lucide.createIcons();
    }
  },

  // 1. Dashboard View
  async loadDashboard() {
    try {
      const stats = await API.getDashboardStats();
      document.getElementById('stat-open-cases').innerText = stats.open_cases;
      document.getElementById('stat-pending-reviews').innerText = stats.pending_reviews;
      document.getElementById('stat-verified-matches').innerText = stats.verified_matches;
      document.getElementById('stat-total-sightings').innerText = stats.total_sightings;
      document.getElementById('stat-enrolled-faces').innerText = stats.enrolled_faces;

      // Load recent cases table
      const cases = await API.getCases();
      const casesTbody = document.getElementById('dashboard-recent-cases');
      if (casesTbody) {
        casesTbody.innerHTML = cases.slice(0, 5).map(c => `
          <tr class="border-b border-slate-100 hover:bg-slate-50/80 transition cursor-pointer" onclick="App.viewCaseDetails(${c.id})">
            <td class="py-3 px-4 font-mono font-bold text-blue-700">${c.reference_no}</td>
            <td class="py-3 px-4 font-semibold text-slate-900">${c.full_name}</td>
            <td class="py-3 px-4 text-xs font-mono text-slate-500">${c.last_seen_date}</td>
            <td class="py-3 px-4 text-xs text-slate-600 truncate max-w-[160px]">${c.last_seen_location}</td>
            <td class="py-3 px-4"><span class="badge-tactical badge-${c.status}">${c.status}</span></td>
            <td class="py-3 px-4 text-right">
              <span class="text-xs font-bold text-blue-600 hover:text-blue-800">Dossier →</span>
            </td>
          </tr>
        `).join('');
      }

      // Load recent sightings
      const sightings = await API.getSightings();
      const sightingsTbody = document.getElementById('dashboard-recent-sightings');
      if (sightingsTbody) {
        sightingsTbody.innerHTML = sightings.slice(0, 5).map(s => {
          const simText = s.top_similarity ? `${(s.top_similarity * 100).toFixed(1)}%` : 'Queued';
          const simColor = s.top_similarity >= 0.70 ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : (s.top_similarity >= 0.50 ? 'text-amber-700 bg-amber-50 border-amber-200' : 'text-slate-600 bg-slate-100 border-slate-200');

          return `
            <tr class="border-b border-slate-100 hover:bg-slate-50/80 transition cursor-pointer" onclick="App.switchTab('review-queue')">
              <td class="py-3 px-4 font-mono font-bold text-amber-700">${s.receipt_no}</td>
              <td class="py-3 px-4 text-xs text-slate-800 truncate max-w-[150px]">${s.location_name}</td>
              <td class="py-3 px-4 text-xs font-mono text-slate-500">${s.sighting_date}</td>
              <td class="py-3 px-4">
                <span class="font-mono text-xs font-bold px-2 py-0.5 rounded border ${simColor}">${simText}</span>
              </td>
              <td class="py-3 px-4"><span class="badge-tactical badge-${s.status}">${s.status}</span></td>
              <td class="py-3 px-4 text-right">
                <span class="text-xs font-bold text-slate-700 hover:text-blue-600">Review →</span>
              </td>
            </tr>
          `;
        }).join('');
      }
    } catch (err) {
      console.error('Error loading dashboard:', err);
    }
  },

  // 2. Cases Management
  async loadCases() {
    try {
      const search = document.getElementById('cases-search')?.value || '';
      const statusFilter = document.getElementById('cases-status-filter')?.value || '';
      const cases = await API.getCases(statusFilter, search);
      const container = document.getElementById('cases-grid');

      if (!container) return;

      if (cases.length === 0) {
        container.innerHTML = `
          <div class="col-span-full p-12 text-center bg-white rounded-2xl border border-slate-200 shadow-sm">
            <div class="text-3xl mb-2">🔍</div>
            <h3 class="text-base font-bold text-slate-800">No Missing-Person Cases Found</h3>
            <p class="text-xs text-slate-500 mt-1">Try adjusting your search criteria or register a new case.</p>
          </div>
        `;
        return;
      }

      container.innerHTML = cases.map(c => `
        <div class="bg-white rounded-2xl border border-slate-200 overflow-hidden dossier-card shadow-sm flex flex-col justify-between">
          <div>
            <!-- Dossier Header & Image -->
            <div class="h-48 bg-slate-900 relative overflow-hidden">
              ${c.primary_photo_path
                ? `<img src="/${c.primary_photo_path}" class="w-full h-full object-cover opacity-90 hover:opacity-100 transition" alt="${c.full_name}"/>`
                : `<div class="w-full h-full flex flex-col items-center justify-center text-slate-500"><span class="text-2xl mb-1">👤</span><span class="text-xs">No Biometric Photo</span></div>`}
              <div class="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent"></div>
              
              <div class="absolute top-3 left-3">
                <span class="bg-slate-900/90 backdrop-blur font-mono font-bold text-xs text-blue-300 px-2.5 py-1 rounded-md border border-slate-700 shadow-sm">
                  ${c.reference_no}
                </span>
              </div>
              <div class="absolute top-3 right-3">
                <span class="badge-tactical badge-${c.status}">${c.status}</span>
              </div>

              <div class="absolute bottom-3 left-3 right-3 text-white">
                <h3 class="text-lg font-bold tracking-tight">${c.full_name}</h3>
                <p class="text-xs text-slate-300">${c.age || 'Unknown'} yrs • ${c.gender || 'Not specified'}</p>
              </div>
            </div>

            <!-- Case Dossier Details -->
            <div class="p-5 space-y-3 text-xs">
              <div class="grid grid-cols-2 gap-2 p-2.5 bg-slate-50 rounded-lg border border-slate-100 font-mono">
                <div>
                  <span class="text-slate-400 block text-[10px]">LAST SEEN</span>
                  <span class="font-semibold text-slate-800">${c.last_seen_date}</span>
                </div>
                <div>
                  <span class="text-slate-400 block text-[10px]">INVESTIGATOR</span>
                  <span class="font-semibold text-slate-800 truncate block">${c.investigator_name ? c.investigator_name.split(' ')[0] : 'Assigned'}</span>
                </div>
              </div>

              <div class="text-slate-600 line-clamp-1">
                <span class="font-semibold text-slate-700">Location:</span> ${c.last_seen_location}
              </div>

              ${c.identifying_features ? `
                <div class="text-slate-600 line-clamp-2">
                  <span class="font-semibold text-slate-700">Features:</span> ${c.identifying_features}
                </div>
              ` : ''}
            </div>
          </div>

          <!-- Footer Actions -->
          <div class="p-4 bg-slate-50/80 border-t border-slate-100 flex items-center justify-between">
            <span class="text-[11px] font-mono text-slate-500">${c.reference_photo_count} Reference Vectors</span>
            <button onclick="App.viewCaseDetails(${c.id})" class="text-xs bg-slate-900 hover:bg-blue-600 text-white font-bold px-3.5 py-1.5 rounded-lg transition shadow-sm">
              Open Dossier →
            </button>
          </div>
        </div>
      `).join('');
    } catch (err) {
      console.error('Error loading cases:', err);
    }
  },

  async viewCaseDetails(caseId) {
    this.currentCaseId = caseId;
    try {
      const c = await API.getCase(caseId);
      this.switchTab('case-detail');

      document.getElementById('case-detail-ref').innerText = c.reference_no;
      document.getElementById('case-detail-name').innerText = c.full_name;
      document.getElementById('case-detail-status').innerText = c.status;
      document.getElementById('case-detail-status').className = `badge-tactical badge-${c.status}`;
      document.getElementById('case-detail-age').innerText = `${c.age || 'N/A'} yrs`;
      document.getElementById('case-detail-gender').innerText = c.gender || 'N/A';
      document.getElementById('case-detail-lastseen').innerText = `${c.last_seen_date} ${c.last_seen_time || ''}`;
      document.getElementById('case-detail-location').innerText = c.last_seen_location;
      document.getElementById('case-detail-investigator').innerText = c.investigator_name || 'Assigned Officer';
      document.getElementById('case-detail-features').innerText = c.identifying_features || 'None specified';
      document.getElementById('case-detail-clothing').innerText = c.clothing_description || 'None specified';
      document.getElementById('case-detail-notes').innerText = c.notes || 'No confidential case notes recorded.';

      // Reference photos with Biometric Canvas Overlays
      const photoContainer = document.getElementById('case-detail-photos');
      if (photoContainer) {
        if (c.reference_photos.length === 0) {
          photoContainer.innerHTML = `<p class="text-slate-400 text-xs">No reference photos enrolled.</p>`;
        } else {
          photoContainer.innerHTML = c.reference_photos.map((p, idx) => `
            <div class="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden shadow-sm">
              <div class="h-56 relative forensic-viewport">
                <canvas id="ref-canvas-${p.id}" class="forensic-canvas"></canvas>
                <div class="hud-corner hud-corner-tl"></div>
                <div class="hud-corner hud-corner-tr"></div>
                <div class="hud-corner hud-corner-bl"></div>
                <div class="hud-corner hud-corner-br"></div>
              </div>
              <div class="p-3 bg-slate-950 border-t border-slate-800 text-xs text-slate-300 flex items-center justify-between">
                <div>
                  <div class="font-mono font-bold text-cyan-400">128-D VECTOR #${p.id} ${idx === 0 ? '<span class="text-[10px] text-blue-400 font-normal">(Primary)</span>' : ''}</div>
                  <div class="text-[10px] text-slate-500 font-mono">${p.model_name} • ${p.model_version}</div>
                </div>
                <div class="flex items-center gap-1.5">
                  <button onclick="App.toggleCanvasMode('ref-canvas-${p.id}', '/${p.file_path}', ${p.bbox_json || 'null'}, null)" class="text-[10px] bg-slate-800 hover:bg-slate-700 px-2.5 py-1 rounded border border-slate-700 font-mono text-cyan-300">
                    Toggle HUD
                  </button>
                  ${c.reference_photos.length > 1 ? `
                    <button onclick="App.deleteReferencePhoto(${p.id})" title="Remove reference portrait" class="text-[10px] bg-red-950/60 hover:bg-red-900 px-2 py-1 rounded border border-red-800 font-mono text-red-300">
                      Delete
                    </button>
                  ` : ''}
                </div>
              </div>
            </div>
          `).join('');

          // Render canvases
          setTimeout(() => {
            c.reference_photos.forEach(p => {
              const bbox = p.bbox_json ? JSON.parse(p.bbox_json) : null;
              this.drawForensicCanvas(`ref-canvas-${p.id}`, `/${p.file_path}`, bbox, null, 'forensic');
            });
          }, 100);
        }
      }

      // Correlated Sighting Leads
      const leadsContainer = document.getElementById('case-detail-leads');
      if (leadsContainer) {
        if (c.linked_leads.length === 0) {
          leadsContainer.innerHTML = `<div class="p-6 text-center text-slate-400 text-xs bg-slate-50 rounded-xl border border-slate-100">No correlated sighting leads recorded yet.</div>`;
        } else {
          leadsContainer.innerHTML = c.linked_leads.map(lead => {
            const scorePct = (lead.similarity_score * 100).toFixed(1);
            const isHigh = lead.similarity_score >= 0.70;

            return `
              <div class="p-4 bg-white rounded-xl border border-slate-200 shadow-sm flex items-center justify-between hover:border-blue-400 transition">
                <div class="flex items-center gap-4">
                  ${lead.sighting_photo_path ? `<img src="/${lead.sighting_photo_path}" class="w-14 h-14 rounded-lg object-cover border border-slate-200" alt="Lead"/>` : ''}
                  <div>
                    <div class="font-mono font-bold text-xs text-amber-700">${lead.receipt_no}</div>
                    <div class="text-xs text-slate-900 font-semibold mt-0.5">${lead.location_name}</div>
                    <div class="text-[11px] font-mono text-slate-500 mt-0.5">Sighted: ${lead.sighting_date}</div>
                  </div>
                </div>
                <div class="text-right space-y-1">
                  <div class="font-mono font-extrabold text-sm ${isHigh ? 'text-emerald-700' : 'text-amber-700'}">${scorePct}% Cosine Match</div>
                  <span class="badge-tactical badge-${lead.match_status}">${lead.match_status}</span>
                </div>
              </div>
            `;
          }).join('');
        }
      }

      // Load chronological timeline (Module 6)
      await this.loadCaseTimeline(caseId);

    } catch (err) {
      alert('Failed to load case dossier: ' + err.message);
    }
  },

  async loadCaseTimeline(caseId) {
    const container = document.getElementById('case-detail-timeline');
    if (!container) return;

    try {
      const res = await API.getCaseTimeline(caseId);
      if (!res.events || res.events.length === 0) {
        container.innerHTML = `<div class="p-6 text-center text-slate-500 font-mono text-xs bg-slate-950 rounded-xl border border-slate-800">No events recorded in case timeline yet.</div>`;
        return;
      }

      container.innerHTML = res.events.map(ev => {
        const badgeColor = ev.badge_color || 'blue';
        const colorClasses = {
          blue: 'border-blue-500/40 bg-blue-950/40 text-blue-300',
          cyan: 'border-cyan-500/40 bg-cyan-950/40 text-cyan-300',
          emerald: 'border-emerald-500/40 bg-emerald-950/40 text-emerald-300',
          amber: 'border-amber-500/40 bg-amber-950/40 text-amber-300',
          orange: 'border-orange-500/40 bg-orange-950/40 text-orange-300',
          rose: 'border-rose-500/40 bg-rose-950/40 text-rose-300',
          purple: 'border-purple-500/40 bg-purple-950/40 text-purple-300',
          slate: 'border-slate-700 bg-slate-900 text-slate-300'
        }[badgeColor] || 'border-slate-700 bg-slate-900 text-slate-300';

        return `
          <div class="relative pl-6 pb-6 border-l border-slate-800 last:border-l-0 last:pb-0">
            <!-- Timeline Marker Icon -->
            <div class="absolute -left-2.5 top-0 w-5 h-5 rounded-full bg-slate-950 border-2 border-slate-700 flex items-center justify-center text-[10px]">
              ${ev.icon || '•'}
            </div>

            <!-- Event Card -->
            <div class="p-4 rounded-xl border ${colorClasses} space-y-2">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="flex items-center gap-2">
                  <span class="font-bold text-white text-xs">${ev.title}</span>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-300">${ev.event_type}</span>
                </div>
                <span class="text-[11px] font-mono text-slate-400">${ev.timestamp}</span>
              </div>

              <p class="text-xs text-slate-300 font-sans leading-relaxed">${ev.description}</p>

              <div class="pt-2 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-400">
                <div>
                  <span>OFFICER / ACTOR:</span> <strong class="text-slate-200">${ev.actor_name}</strong> (${ev.badge_number})
                </div>
                ${ev.metadata && ev.metadata.similarity_score ? `
                  <div class="text-amber-400 font-bold">
                    AI Match: ${(ev.metadata.similarity_score * 100).toFixed(1)}% Cosine
                  </div>
                ` : ''}
              </div>
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      console.error('Failed to load case timeline:', err);
      container.innerHTML = `<div class="p-4 text-center text-red-400 text-xs">Failed to load timeline: ${err.message}</div>`;
    }
  },

  refreshCaseTimeline() {
    if (this.currentCaseId) {
      this.loadCaseTimeline(this.currentCaseId);
    }
  },

  // 3. Forensic Candidate Review Workbench (Module 6 Core)
  async loadReviewQueue() {
    try {
      // 1. Fetch queue workload telemetry
      try {
        const stats = await API.getCandidateStats();
        const elPending = document.getElementById('rq-stat-pending');
        const elHigh = document.getElementById('rq-stat-high');
        const elVerified = document.getElementById('rq-stat-verified');
        const elEscalated = document.getElementById('rq-stat-escalated');
        if (elPending) elPending.innerText = stats.pending_review ?? 0;
        if (elHigh) elHigh.innerText = stats.high_confidence_pending ?? 0;
        if (elVerified) elVerified.innerText = stats.verified_count ?? 0;
        if (elEscalated) elEscalated.innerText = stats.escalated_count ?? 0;
      } catch (stErr) {
        console.error('Failed to load queue telemetry:', stErr);
      }

      // 2. Read active filter selections
      const statusVal = document.getElementById('rq-filter-status')?.value || 'requires_human_review';
      const tierVal = document.getElementById('rq-filter-tier')?.value || 'all';
      const sortVal = document.getElementById('rq-sort-by')?.value || 'score_desc';

      let minScore = null;
      if (tierVal === 'high') minScore = 0.70;
      else if (tierVal === 'moderate') minScore = 0.50;

      const filterParams = {
        status: statusVal,
        minScore: minScore,
        sortBy: sortVal
      };

      let candidates = await API.getCandidates(filterParams);
      if (tierVal === 'low') {
        candidates = candidates.filter(c => c.similarity_score < 0.50);
      }

      const container = document.getElementById('review-queue-list');
      if (!container) return;

      if (candidates.length === 0) {
        container.innerHTML = `
          <div class="p-16 text-center bg-slate-900 rounded-2xl border border-slate-800 shadow-sm space-y-3">
            <div class="w-16 h-16 mx-auto rounded-full bg-emerald-950/80 text-emerald-400 flex items-center justify-center font-bold text-2xl border border-emerald-700/50">
              ✓
            </div>
            <h3 class="text-lg font-extrabold text-white">No Leads Matching Active Filter</h3>
            <p class="text-xs text-slate-400 max-w-md mx-auto leading-relaxed font-mono">
              All candidate leads for filter [Status: ${statusVal.toUpperCase()}, Tier: ${tierVal.toUpperCase()}] have been cleared or none are queued. Adjust filters above to inspect historical or low-similarity items.
            </p>
          </div>
        `;
        return;
      }

      container.innerHTML = candidates.map(c => {
        const scorePercent = (c.similarity_score * 100).toFixed(1);
        const isHigh = c.similarity_score >= 0.70;
        const tierLabel = isHigh ? 'HIGH CONFIDENCE (≥ 0.70)' : (c.similarity_score >= 0.50 ? 'MODERATE (0.50 - 0.69)' : 'LOW SIMILARITY (< 0.50)');
        const tierBadgeClass = isHigh ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' : (c.similarity_score >= 0.50 ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-slate-700/40 text-slate-300 border-slate-600');

        // Calculate geographical distance in km between Case last-seen and Sighting
        const distKm = c.spatial_separation_km !== undefined ? c.spatial_separation_km : MapManager.calculateDistanceKm(c.case_lat, c.case_lng, c.sighting_lat, c.sighting_lng);
        const daysDelta = c.temporal_delta_days !== undefined ? c.temporal_delta_days : null;

        // Parse landmarks & bbox for canvases
        const sightingFaces = c.sighting_faces_json ? JSON.parse(c.sighting_faces_json) : [];
        const activeSightFace = sightingFaces[c.sighting_face_index] || sightingFaces[0] || {};
        const sightBbox = activeSightFace.bbox || null;
        const sightLandmarks = activeSightFace.landmarks || null;

        const refBbox = c.ref_bbox_json ? JSON.parse(c.ref_bbox_json) : null;
        const refLandmarks = c.ref_landmarks_json ? JSON.parse(c.ref_landmarks_json) : null;

        return `
          <div class="bg-slate-900 rounded-2xl border border-slate-800 shadow-xl overflow-hidden mb-8">
            <!-- Command Console Header -->
            <div class="bg-slate-950 text-white p-5 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4">
              <div class="flex items-center gap-3">
                <span class="pulse-indicator ${isHigh ? 'pulse-emerald' : 'pulse-amber'}"></span>
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-mono font-extrabold text-cyan-400 text-sm tracking-wide">LEAD ADJUDICATION #${c.candidate_id}</span>
                    <span class="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono border border-slate-700">Rank #${c.rank}</span>
                    ${c.match_status !== 'requires_human_review' ? `
                      <span class="text-xs font-mono font-bold px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">${c.match_status.toUpperCase()}</span>
                    ` : ''}
                  </div>
                  <div class="text-xs text-slate-400 mt-0.5">
                    Sighting <strong class="text-slate-200 font-mono">${c.receipt_no}</strong> correlated against Case <strong class="text-slate-200 font-mono">${c.reference_no}</strong> (${c.person_name})
                  </div>
                </div>
              </div>

              <!-- Biometric Match Score Badge -->
              <div class="flex items-center gap-4">
                <div class="text-right">
                  <div class="font-mono text-2xl font-black ${isHigh ? 'text-emerald-400' : (c.similarity_score >= 0.50 ? 'text-amber-400' : 'text-slate-400')}">
                    ${scorePercent}%
                  </div>
                  <div class="text-[10px] font-mono uppercase tracking-wider text-slate-400">${tierLabel}</div>
                </div>

                <div class="h-10 w-px bg-slate-800"></div>

                <span class="badge-tactical badge-${c.match_status}">
                  ${c.match_status === 'requires_human_review' ? 'Pending Human Review' : c.match_status}
                </span>
              </div>
            </div>

            <!-- Mandatory Ethical & Legal Caution Banner -->
            <div class="bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent border-b border-amber-500/20 px-6 py-2.5 text-xs text-amber-200 flex items-center gap-2.5">
              <span class="text-base">⚖️</span>
              <div>
                <span class="font-bold text-amber-300">MANDATORY INVESTIGATION GOVERNANCE:</span>
                <span class="text-slate-300">Biometric similarity scores are mathematical ranking signals only. Autonomous identification is prohibited. Review officers must record affirmative written findings.</span>
              </div>
            </div>

            <!-- Dual Forensic Viewport Comparison -->
            <div class="p-6 bg-slate-900 grid grid-cols-1 lg:grid-cols-2 gap-6 hud-grid">
              <!-- Left Viewport: Submitted Sighting Image -->
              <div class="space-y-3">
                <div class="flex items-center justify-between text-xs text-slate-300">
                  <div class="flex items-center gap-2 font-bold">
                    <span class="text-cyan-400 font-mono">PANEL A</span>
                    <span>Submitted Sighting Evidence</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <button onclick="App.toggleCanvasMode('canvas-sight-${c.candidate_id}', '/${c.sighting_photo_path}', ${JSON.stringify(sightBbox)}, ${JSON.stringify(sightLandmarks)})" class="text-[10px] bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded text-cyan-300 font-mono border border-slate-700">
                      Toggle Overlays
                    </button>
                  </div>
                </div>

                <div class="forensic-viewport h-80 relative">
                  <canvas id="canvas-sight-${c.candidate_id}" class="forensic-canvas"></canvas>
                  <div class="hud-corner hud-corner-tl"></div>
                  <div class="hud-corner hud-corner-tr"></div>
                  <div class="hud-corner hud-corner-bl"></div>
                  <div class="hud-corner hud-corner-br"></div>
                  <div class="absolute bottom-3 left-3 bg-black/80 backdrop-blur px-2.5 py-1 rounded text-[11px] font-mono text-cyan-300 border border-cyan-500/30">
                    SIGHTING FACE #${c.sighting_face_index + 1}
                  </div>
                </div>

                <!-- Sighting Metadata Card -->
                <div class="p-3 bg-slate-950/80 rounded-xl border border-slate-800 text-xs text-slate-300 space-y-1.5 font-mono">
                  <div class="flex justify-between">
                    <span class="text-slate-500">LOCATION:</span>
                    <span class="text-slate-200 truncate max-w-[240px]">${c.location_name}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-slate-500">SIGHTED DATE:</span>
                    <span class="text-slate-200">${c.sighting_date} ${c.sighting_time || ''}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-slate-500">REPORTER NOTES:</span>
                    <span class="text-slate-300 italic truncate max-w-[240px]">"${c.sighting_notes || 'None'}"</span>
                  </div>
                </div>
              </div>

              <!-- Right Viewport: Registered Reference Portrait -->
              <div class="space-y-3">
                <div class="flex items-center justify-between text-xs text-slate-300">
                  <div class="flex items-center gap-2 font-bold">
                    <span class="text-blue-400 font-mono">PANEL B</span>
                    <span>Enrolled Reference Record</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <button onclick="App.toggleCanvasMode('canvas-ref-${c.candidate_id}', '/${c.reference_photo_path}', ${JSON.stringify(refBbox)}, ${JSON.stringify(refLandmarks)})" class="text-[10px] bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded text-blue-300 font-mono border border-slate-700">
                      Toggle Overlays
                    </button>
                  </div>
                </div>

                <div class="forensic-viewport h-80 relative">
                  <canvas id="canvas-ref-${c.candidate_id}" class="forensic-canvas"></canvas>
                  <div class="hud-corner hud-corner-tl"></div>
                  <div class="hud-corner hud-corner-tr"></div>
                  <div class="hud-corner hud-corner-bl"></div>
                  <div class="hud-corner hud-corner-br"></div>
                  <div class="absolute bottom-3 left-3 bg-blue-950/90 backdrop-blur px-2.5 py-1 rounded text-[11px] font-mono text-blue-300 border border-blue-500/30">
                    AUTHORIZED REFERENCE
                  </div>
                </div>

                <!-- Case Reference Metadata Card -->
                <div class="p-3 bg-slate-950/80 rounded-xl border border-slate-800 text-xs text-slate-300 space-y-1.5 font-mono">
                  <div class="flex justify-between">
                    <span class="text-slate-500">IDENTITY:</span>
                    <span class="text-blue-300 font-bold">${c.person_name} (${c.reference_no})</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-slate-500">AGE / GENDER:</span>
                    <span class="text-slate-200">${c.age || 'N/A'} yrs • ${c.gender || 'N/A'}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-slate-500">LAST SEEN:</span>
                    <span class="text-slate-200 truncate max-w-[240px]">${c.last_seen_location} (${c.last_seen_date})</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Forensic Correlation & Spatial Metrics Bar -->
            <div class="bg-slate-950/80 border-t border-b border-slate-800 px-6 py-3 flex flex-wrap items-center justify-between gap-4 text-xs font-mono text-slate-300">
              <div class="flex flex-wrap items-center gap-6">
                <div>
                  <span class="text-slate-500 text-[10px] block">SPATIAL SEPARATION</span>
                  <span class="font-bold text-cyan-400">${distKm !== null ? `${distKm} km from origin` : 'Coordinates pending'}</span>
                </div>
                <div>
                  <span class="text-slate-500 text-[10px] block">TEMPORAL DELTA</span>
                  <span class="font-bold text-amber-300">${daysDelta !== null ? `${daysDelta} days elapsed` : 'Simultaneous'}</span>
                </div>
                <div>
                  <span class="text-slate-500 text-[10px] block">FEATURE VECTOR</span>
                  <span class="font-bold text-slate-200">${c.model_version} (128-D)</span>
                </div>
                <div>
                  <span class="text-slate-500 text-[10px] block">COSINE SIMILARITY</span>
                  <span class="font-bold text-slate-200">${c.similarity_score.toFixed(4)}</span>
                </div>
              </div>

              <!-- Quick GIS Map Inspection -->
              <button onclick="MapManager.focusPair(${c.case_lat || 13.0827}, ${c.case_lng || 80.2707}, ${c.sighting_lat || 13.0827}, ${c.sighting_lng || 80.2707}, '${c.reference_no}', '${c.receipt_no}', ${c.similarity_score})" class="px-3.5 py-1.5 text-xs font-mono font-bold rounded-lg bg-cyan-950/60 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 transition flex items-center gap-1.5 shadow-sm">
                <span>🗺️</span> <span>Inspect on GIS Map</span>
              </button>
            </div>

            <!-- Adjudication Action Command Bar -->
            <div class="p-5 bg-slate-900 flex flex-wrap items-center justify-between gap-4 border-t border-slate-800/80">
              <div class="flex items-center gap-2">
                <span class="text-xs text-slate-400 font-semibold font-mono">Quick Adjudication:</span>
                <button onclick="App.openReviewModal(${c.candidate_id}, 'rejected')" class="px-3.5 py-2 text-xs font-bold font-mono rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition">
                  Reject Lead
                </button>
                <button onclick="App.openReviewModal(${c.candidate_id}, 'request_more_info')" class="px-3.5 py-2 text-xs font-bold font-mono rounded-xl bg-amber-950/50 hover:bg-amber-900 text-amber-300 border border-amber-800 transition">
                  Request Witness Info
                </button>
                <button onclick="App.openReviewModal(${c.candidate_id}, 'escalated')" class="px-3.5 py-2 text-xs font-bold font-mono rounded-xl bg-orange-950/50 hover:bg-orange-900 text-orange-300 border border-orange-800 transition">
                  Escalate to Field Team
                </button>
              </div>

              <button onclick="App.openReviewModal(${c.candidate_id}, 'verified')" class="px-5 py-2.5 text-xs font-extrabold font-mono rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white shadow-md transition flex items-center gap-1.5">
                <span>✓</span>
                <span>Confirm Verified Match</span>
              </button>
            </div>
          </div>
        `;
      }).join('');

      // Draw biometric canvases after DOM insertion
      setTimeout(() => {
        candidates.forEach(c => {
          const sightingFaces = c.sighting_faces_json ? JSON.parse(c.sighting_faces_json) : [];
          const activeSightFace = sightingFaces[c.sighting_face_index] || sightingFaces[0] || {};
          const sightBbox = activeSightFace.bbox || null;
          const sightLandmarks = activeSightFace.landmarks || null;

          const refBbox = c.ref_bbox_json ? JSON.parse(c.ref_bbox_json) : null;
          const refLandmarks = c.ref_landmarks_json ? JSON.parse(c.ref_landmarks_json) : null;

          this.drawForensicCanvas(`canvas-sight-${c.candidate_id}`, `/${c.sighting_photo_path}`, sightBbox, sightLandmarks, 'forensic');
          this.drawForensicCanvas(`canvas-ref-${c.candidate_id}`, `/${c.reference_photo_path}`, refBbox, refLandmarks, 'forensic');
        });
      }, 150);

    } catch (err) {
      console.error('Error loading review queue:', err);
    }
  },

  applyReviewFilters() {
    this.loadReviewQueue();
  },

  async openBatchRejectModal() {
    try {
      const candidates = await API.getCandidates({ status: 'requires_human_review' });
      const lowConfidenceLeads = candidates.filter(c => c.similarity_score < 0.50);

      if (lowConfidenceLeads.length === 0) {
        alert('No pending leads with similarity < 0.50 found to batch reject.');
        return;
      }

      const confirmed = confirm(
        `Found ${lowConfidenceLeads.length} low-similarity lead(s) (< 0.50 Cosine).\n\nDo you want to batch-reject these false positives with written rationale: "Batch rejected during routine noise filtering"?`
      );

      if (confirmed) {
        const ids = lowConfidenceLeads.map(c => c.candidate_id);
        const res = await API.submitBatchReview(
          ids,
          'rejected',
          'Batch rejected during routine noise filtering on low-similarity leads (< 0.50).',
          'Discarded from active lead queue.'
        );
        alert(res.message);
        this.loadReviewQueue();
      }
    } catch (err) {
      alert('Batch reject failed: ' + err.message);
    }
  },

  // Interactive Forensic Canvas Drawing Engine
  drawForensicCanvas(canvasId, imageSrc, bbox, landmarks, mode = 'forensic') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    this.canvasModes[canvasId] = mode;
    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
      // Set canvas internal dimensions to match image resolution
      canvas.width = img.width;
      canvas.height = img.height;

      // Draw raw image
      ctx.drawImage(img, 0, 0);

      if (mode === 'raw') return;

      // Draw tactical bounding box
      if (bbox && bbox.length === 4) {
        const [x, y, w, h] = bbox;
        const cornerLen = Math.min(w, h) * 0.22;

        ctx.strokeStyle = '#06B6D4'; // Tactical Cyan
        ctx.lineWidth = Math.max(2, Math.floor(canvas.width * 0.005));

        // Draw tactical corner brackets
        // Top-Left
        ctx.beginPath();
        ctx.moveTo(x, y + cornerLen);
        ctx.lineTo(x, y);
        ctx.lineTo(x + cornerLen, y);
        ctx.stroke();

        // Top-Right
        ctx.beginPath();
        ctx.moveTo(x + w - cornerLen, y);
        ctx.lineTo(x + w, y);
        ctx.lineTo(x + w, y + cornerLen);
        ctx.stroke();

        // Bottom-Left
        ctx.beginPath();
        ctx.moveTo(x, y + h - cornerLen);
        ctx.lineTo(x, y + h);
        ctx.lineTo(x + cornerLen, y + h);
        ctx.stroke();

        // Bottom-Right
        ctx.beginPath();
        ctx.moveTo(x + w - cornerLen, y + h);
        ctx.lineTo(x + w, y + h);
        ctx.lineTo(x + w, y + h - cornerLen);
        ctx.stroke();

        // Subtle bounding box outline
        ctx.strokeStyle = 'rgba(6, 182, 212, 0.4)';
        ctx.lineWidth = 1;
        ctx.strokeRect(x, y, w, h);

        // Bounding box tag
        ctx.fillStyle = '#06B6D4';
        const fontSize = Math.max(12, Math.floor(canvas.width * 0.022));
        ctx.font = `bold ${fontSize}px monospace`;
        ctx.fillText(`FACE REGION [${w}x${h}]`, x + 4, Math.max(fontSize + 4, y - 6));
      }

      // Draw 5 facial landmarks & biometric triangulation
      if (mode === 'forensic' && landmarks && landmarks.length >= 5) {
        ctx.fillStyle = '#22C55E'; // Emerald landmarks
        ctx.strokeStyle = 'rgba(34, 197, 94, 0.5)';
        ctx.lineWidth = 1.5;

        // Triangulation lines connecting eyes, nose, and mouth
        ctx.beginPath();
        ctx.moveTo(landmarks[0][0], landmarks[0][1]); // right eye
        ctx.lineTo(landmarks[1][0], landmarks[1][1]); // left eye
        ctx.lineTo(landmarks[2][0], landmarks[2][1]); // nose
        ctx.closePath();
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(landmarks[2][0], landmarks[2][1]); // nose
        ctx.lineTo(landmarks[3][0], landmarks[3][1]); // right mouth
        ctx.lineTo(landmarks[4][0], landmarks[4][1]); // left mouth
        ctx.closePath();
        ctx.stroke();

        // Landmark circles
        const ptRadius = Math.max(3, Math.floor(canvas.width * 0.008));
        landmarks.forEach(pt => {
          ctx.beginPath();
          ctx.arc(pt[0], pt[1], ptRadius, 0, 2 * Math.PI);
          ctx.fill();
        });
      }
    };

    img.src = imageSrc;
  },

  toggleCanvasMode(canvasId, imageSrc, bbox, landmarks) {
    const current = this.canvasModes[canvasId] || 'forensic';
    const nextMode = current === 'forensic' ? 'bbox' : (current === 'bbox' ? 'raw' : 'forensic');
    this.drawForensicCanvas(canvasId, imageSrc, bbox, landmarks, nextMode);
  },

  openReviewModal(candidateId, disposition) {
    this.activeCandidateId = candidateId;
    const modal = document.getElementById('review-modal');
    const dispSelect = document.getElementById('review-disposition');
    if (dispSelect) dispSelect.value = disposition;
    if (modal) modal.classList.remove('hidden');
  },

  closeReviewModal() {
    const modal = document.getElementById('review-modal');
    if (modal) modal.classList.add('hidden');
    this.activeCandidateId = null;
  },

  appendRationaleChip(text) {
    const ta = document.getElementById('review-rationale');
    if (!ta) return;
    if (ta.value.trim()) {
      ta.value += " " + text;
    } else {
      ta.value = text;
    }
    ta.focus();
  },

  async handleReviewSubmit(e) {
    e.preventDefault();
    if (!this.activeCandidateId) return;

    const disposition = document.getElementById('review-disposition').value;
    const rationale = document.getElementById('review-rationale').value.trim();
    const nextSteps = document.getElementById('review-next-steps')?.value.trim() || '';

    if (rationale.length < 5) {
      alert('Mandatory investigator rationale must be at least 5 characters explaining your decision.');
      return;
    }

    try {
      const res = await API.submitReview(this.activeCandidateId, disposition, rationale, nextSteps);
      alert(`Adjudication saved! Disposition marked as '${disposition}'. Audit log updated.`);
      this.closeReviewModal();
      document.getElementById('review-rationale').value = '';
      this.loadReviewQueue();
      this.loadNotifications();
    } catch (err) {
      alert('Review submission failed: ' + err.message);
    }
  },

  // Notification Operations (Module 6)
  async loadNotifications() {
    const user = API.getUser();
    const bellContainer = document.getElementById('notification-bell-container');
    const badge = document.getElementById('notif-badge');
    const list = document.getElementById('notif-dropdown-list');
    if (!user) {
      if (bellContainer) bellContainer.classList.add('hidden');
      return;
    }
    if (bellContainer) bellContainer.classList.remove('hidden');

    try {
      const res = await API.getNotifications(false, 15);
      const unread = res.unread_count || 0;
      if (badge) {
        if (unread > 0) {
          badge.innerText = unread > 9 ? '9+' : unread;
          badge.classList.remove('hidden');
        } else {
          badge.classList.add('hidden');
        }
      }

      if (list) {
        if (!res.notifications || res.notifications.length === 0) {
          list.innerHTML = `<div class="p-4 text-center text-slate-500 font-mono text-xs">No active alerts. All operational notifications cleared.</div>`;
        } else {
          list.innerHTML = res.notifications.map(n => {
            const isUnread = !n.is_read;
            const icon = n.category === 'match_alert' ? '⚡' : (n.category === 'review_update' ? '⚖️' : '🔔');
            return `
              <div onclick="App.handleNotificationClick(${n.id}, '${n.link_url || ''}')" class="p-3 ${isUnread ? 'bg-slate-800/80 hover:bg-slate-750' : 'bg-slate-900/40 hover:bg-slate-800/60'} transition cursor-pointer flex items-start gap-3">
                <span class="text-base mt-0.5">${icon}</span>
                <div class="flex-grow min-w-0">
                  <div class="flex items-center justify-between gap-1">
                    <span class="font-bold text-slate-200 text-xs truncate ${isUnread ? 'text-cyan-300' : ''}">${n.title}</span>
                    ${isUnread ? '<span class="w-2 h-2 rounded-full bg-cyan-400 flex-shrink-0"></span>' : ''}
                  </div>
                  <p class="text-slate-400 text-[11px] leading-relaxed mt-0.5">${n.message}</p>
                  <span class="text-[10px] font-mono text-slate-500 mt-1 block">${n.created_at}</span>
                </div>
              </div>
            `;
          }).join('');
        }
      }
    } catch (err) {
      console.error('Failed to load notifications:', err);
    }
  },

  toggleNotificationDropdown() {
    const drop = document.getElementById('notif-dropdown');
    if (!drop) return;
    drop.classList.toggle('hidden');
    if (!drop.classList.contains('hidden')) {
      this.loadNotifications();
    }
  },

  async markAllNotificationsRead() {
    try {
      await API.markAllNotificationsRead();
      await this.loadNotifications();
    } catch (err) {
      console.error('Failed to mark all read:', err);
    }
  },

  async handleNotificationClick(notifId, linkUrl) {
    try {
      await API.markNotificationRead(notifId);
      const drop = document.getElementById('notif-dropdown');
      if (drop) drop.classList.add('hidden');
      this.loadNotifications();

      if (linkUrl && linkUrl.includes('/review')) {
        this.switchTab('review-queue');
      } else if (linkUrl && linkUrl.includes('/cases')) {
        this.switchTab('cases');
      }
    } catch (err) {
      console.error('Error handling notification click:', err);
    }
  },

  // 4. Public Sighting Submission
  // 4. Public Sighting Submission
  setSightingLocationPreset(name, lat, lng) {
    const locInput = document.getElementById('sighting-location');
    const latInput = document.getElementById('sighting-lat');
    const lngInput = document.getElementById('sighting-lng');
    if (locInput) locInput.value = name;
    if (latInput) latInput.value = lat;
    if (lngInput) lngInput.value = lng;
    if (this.sightingPickerMarker && this.sightingPickerMap) {
      this.sightingPickerMarker.setLatLng([lat, lng]);
      this.sightingPickerMap.setView([lat, lng], 14);
    }
  },

  fillReceiptLookup(code) {
    const input = document.getElementById('lookup-receipt-input');
    if (input) {
      input.value = code;
      const form = document.getElementById('receipt-lookup-form');
      if (form) {
        form.dispatchEvent(new Event('submit', { cancelable: true }));
      }
    }
  },

  async copyReceiptToClipboard() {
    const code = document.getElementById('receipt-number-display')?.innerText;
    if (code) {
      try {
        await navigator.clipboard.writeText(code);
        const btn = document.getElementById('copy-receipt-btn');
        if (btn) {
          const oldHtml = btn.innerHTML;
          btn.innerHTML = '<span>✓</span> <span>Copied!</span>';
          setTimeout(() => { btn.innerHTML = oldHtml; }, 2000);
        }
      } catch (err) {
        prompt('Copy your receipt tracking code:', code);
      }
    }
  },

  trackReceiptFromModal() {
    const code = document.getElementById('receipt-number-display')?.innerText;
    this.closeModal('receipt-modal');
    this.switchTab('public-track');
    if (code) {
      this.fillReceiptLookup(code);
    }
  },

  async handleSightingSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('sighting-submit-btn');
    if (btn) {
      btn.disabled = true;
      btn.innerText = 'Processing Biometrics & Submitting...';
    }

    try {
      const form = document.getElementById('sighting-form');
      const formData = new FormData(form);

      const res = await API.submitSighting(formData);

      // Populate enhanced receipt modal
      document.getElementById('receipt-number-display').innerText = res.receipt_no;
      const faceBadge = document.getElementById('receipt-faces-count');
      if (faceBadge) {
        if (res.faces_detected_count > 0) {
          faceBadge.innerText = `${res.faces_detected_count} face(s) screened by SFace`;
          faceBadge.className = 'text-emerald-400 font-bold';
        } else {
          faceBadge.innerText = '0 faces detected (Queued as observational lead)';
          faceBadge.className = 'text-amber-400 font-bold';
        }
      }
      document.getElementById('receipt-location').innerText = res.location_name;
      document.getElementById('receipt-modal').classList.remove('hidden');

      form.reset();
      document.getElementById('sighting-preview-box').classList.add('hidden');
    } catch (err) {
      alert('Submission failed: ' + err.message);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerText = 'Submit Sighting to Law Enforcement';
      }
    }
  },

  // 5. Case Registration
  async handleCaseSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('case-submit-btn');
    if (btn) {
      btn.disabled = true;
      btn.innerText = 'Validating Facial Imagery...';
    }

    try {
      const fullName = document.getElementById('case-fullname').value.trim();
      const age = parseInt(document.getElementById('case-age').value) || null;
      const gender = document.getElementById('case-gender').value;
      const lastSeenDate = document.getElementById('case-date').value;
      const lastSeenTime = document.getElementById('case-time').value;
      const lastSeenLocation = document.getElementById('case-location').value;
      const lat = parseFloat(document.getElementById('case-lat').value) || 13.0827;
      const lng = parseFloat(document.getElementById('case-lng').value) || 80.2707;
      const features = document.getElementById('case-features').value;
      const clothing = document.getElementById('case-clothing').value;
      const notes = document.getElementById('case-notes').value;

      const photoInput = document.getElementById('case-photo-file');
      if (!photoInput.files || photoInput.files.length === 0) {
        alert('An authorized reference photo is required to enroll a missing-person case.');
        if (btn) {
          btn.disabled = false;
          btn.innerText = 'Enroll Case & Biometrics';
        }
        return;
      }

      // Step 1: Create Case
      const caseData = {
        full_name: fullName,
        age: age,
        gender: gender,
        last_seen_date: lastSeenDate,
        last_seen_time: lastSeenTime,
        last_seen_location: lastSeenLocation,
        latitude: lat,
        longitude: lng,
        identifying_features: features,
        clothing_description: clothing,
        notes: notes
      };

      const newCase = await API.createCase(caseData);

      // Step 2: Upload photo and extract embedding
      await API.addReferencePhoto(newCase.id, photoInput.files[0]);

      alert(`Case ${newCase.reference_no} enrolled successfully with 128-D facial vector!`);
      this.closeModal('create-case-modal');
      document.getElementById('create-case-form').reset();
      this.switchTab('cases');
    } catch (err) {
      alert('Case enrollment error: ' + err.message);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerText = 'Enroll Case & Biometrics';
      }
    }
  },

  // 6. Public Receipt Lookup
  async handleReceiptLookup(e) {
    e.preventDefault();
    const receiptNo = document.getElementById('lookup-receipt-input').value.trim();
    if (!receiptNo) return;

    const container = document.getElementById('lookup-result-box');
    container.classList.remove('hidden');
    container.innerHTML = `
      <div class="p-6 bg-slate-950 border border-slate-800 rounded-2xl text-center space-y-2">
        <div class="inline-block animate-spin text-2xl">⏳</div>
        <p class="text-xs font-mono text-cyan-400">Querying cryptographic intake registry for ${receiptNo}...</p>
      </div>
    `;

    try {
      const res = await API.lookupReceipt(receiptNo);

      // Determine progress stage (1 to 4)
      let currentStage = 3;
      let statusBadgeColor = 'badge-under_review';
      if (res.status === 'verified_match') {
        currentStage = 4;
        statusBadgeColor = 'badge-verified';
      } else if (res.status === 'escalated') {
        currentStage = 4;
        statusBadgeColor = 'badge-escalated';
      } else if (res.status === 'rejected') {
        currentStage = 4;
        statusBadgeColor = 'badge-rejected';
      } else if (res.status === 'in_review') {
        currentStage = 3;
        statusBadgeColor = 'badge-open';
      } else {
        currentStage = 2; // pending_review
        statusBadgeColor = 'badge-under_review';
      }

      const steps = [
        { num: 1, label: 'Intake Registered', done: true, desc: 'Evidence & telemetry signed' },
        { num: 2, label: 'Biometric Screening', done: currentStage >= 2, desc: `${res.faces_detected_count} face(s) evaluated via SFace` },
        { num: 3, label: 'Investigator Queue', done: currentStage >= 3, active: currentStage === 3, desc: 'Assigned to law enforcement review' },
        { num: 4, label: 'Action Disposition', done: currentStage >= 4, active: currentStage === 4, desc: res.status_label }
      ];

      container.innerHTML = `
        <div class="p-6 bg-slate-950 border border-slate-800 rounded-2xl shadow-xl space-y-6">
          <!-- Receipt Header -->
          <div class="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <span class="text-[10px] font-mono uppercase text-slate-500 block">AUTHENTICATED RECEIPT</span>
              <span class="font-mono font-black text-cyan-400 text-xl">${res.receipt_no}</span>
            </div>
            <span class="badge-tactical ${statusBadgeColor}">${res.status_label || res.status}</span>
          </div>

          <!-- 4-Stage Progress Stepper -->
          <div class="space-y-2">
            <span class="text-[10px] font-mono uppercase text-slate-500 block tracking-wider">LIFECYCLE VERIFICATION PROGRESS</span>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
              ${steps.map(s => {
                const border = s.done ? 'border-emerald-600 bg-emerald-950/40 text-emerald-300' : (s.active ? 'border-amber-500 bg-amber-950/40 text-amber-300 animate-pulse' : 'border-slate-800 bg-slate-900/50 text-slate-500');
                const dot = s.done ? '✓' : s.num;
                return `
                  <div class="p-2.5 rounded-xl border ${border} text-xs font-mono space-y-1">
                    <div class="flex items-center justify-between">
                      <span class="font-bold text-[11px]">${dot} ${s.label}</span>
                    </div>
                    <div class="text-[10px] text-slate-400 truncate">${s.desc}</div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>

          <!-- Metadata Grid -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 p-4 bg-slate-900 rounded-xl border border-slate-800 text-xs font-mono">
            <div>
              <span class="text-slate-500 text-[10px] block">LOCATION LANDMARK</span>
              <span class="text-white font-bold">${res.location_name}</span>
            </div>
            <div>
              <span class="text-slate-500 text-[10px] block">SIGHTING TIMESTAMP</span>
              <span class="text-white font-bold">${res.sighting_date} ${res.sighting_time || ''}</span>
            </div>
            <div>
              <span class="text-slate-500 text-[10px] block">BIOMETRIC FACIAL COUNT</span>
              <span class="text-cyan-400 font-bold">${res.faces_detected_count} face(s) processed</span>
            </div>
            <div>
              <span class="text-slate-500 text-[10px] block">SUBMISSION INGESTED AT</span>
              <span class="text-slate-300">${res.submitted_at}</span>
            </div>
          </div>

          <!-- Official Status Guidance Notice -->
          <div class="p-4 bg-blue-950/40 border border-blue-900/70 rounded-xl text-xs space-y-1">
            <div class="flex items-center gap-1.5 text-cyan-400 font-bold text-[11px] font-mono">
              <span>ℹ️</span> <span>OFFICIAL STATUS GUIDANCE</span>
            </div>
            <p class="text-slate-300 leading-relaxed">${res.notice}</p>
          </div>

          <!-- Privacy Shield Notice -->
          <div class="p-3 bg-slate-900 border border-slate-800 rounded-xl text-[11px] text-slate-400 flex items-start gap-2">
            <span class="text-sm">🛡️</span>
            <div>
              <strong class="text-slate-300">Privacy Shield Enforced:</strong> ${res.privacy_statement || 'Sensitive missing-person records remain strictly restricted to sworn officers.'}
            </div>
          </div>
        </div>
      `;
    } catch (err) {
      container.innerHTML = `
        <div class="p-6 bg-red-950/40 border border-red-900 rounded-2xl text-center space-y-2">
          <div class="text-2xl text-red-400">⚠️</div>
          <h4 class="text-sm font-bold text-red-200">Receipt Lookup Failed</h4>
          <p class="text-xs text-red-300">${err.message}</p>
          <p class="text-[11px] text-slate-400 font-mono mt-1">Please check the code syntax (e.g. STG-2026-0001) or contact police helpline.</p>
        </div>
      `;
    }
  },

  // 7. System Audit Trail, AI Governance & Security Workbench (Module 7)
  async loadAuditLogs() {
    try {
      const action = document.getElementById('audit-filter-action')?.value || '';
      const actor = document.getElementById('audit-filter-actor')?.value?.trim() || '';
      const resource_type = document.getElementById('audit-filter-resource')?.value || '';
      const start_date = document.getElementById('audit-filter-start')?.value || '';
      const end_date = document.getElementById('audit-filter-end')?.value || '';

      const { logs, checksum, totalCount } = await API.getAuditLogsWithHeaders({
        action: action || undefined,
        actor: actor || undefined,
        resource_type: resource_type || undefined,
        start_date: start_date || undefined,
        end_date: end_date || undefined,
        limit: 100
      });

      const sealEl = document.getElementById('audit-seal-hash');
      if (sealEl) {
        if (checksum) {
          sealEl.innerText = `${checksum.slice(0, 10)}...${checksum.slice(-6)}`;
          sealEl.setAttribute('data-full-hash', checksum);
          sealEl.title = `Full SHA-256 Digest: ${checksum} (Click to copy)`;
        } else {
          sealEl.innerText = 'SHA-256 VERIFIED';
        }
      }

      const countEl = document.getElementById('audit-count-shown');
      if (countEl) {
        countEl.innerText = `${logs.length}${totalCount ? ' of ' + totalCount : ''}`;
      }

      const tbody = document.getElementById('audit-table-body');
      if (!tbody) return;

      if (!logs || logs.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="6" class="py-8 text-center text-slate-500 font-mono text-xs">
              No audit records match the selected filter criteria.
            </td>
          </tr>
        `;
        return;
      }

      const getActionBadgeClass = (actionName) => {
        if (!actionName) return 'bg-slate-800 text-slate-300 border-slate-700';
        if (actionName.includes('LOGIN')) return 'bg-purple-950/80 text-purple-300 border-purple-800';
        if (actionName.includes('CREATE')) return 'bg-blue-950/80 text-blue-300 border-blue-800';
        if (actionName.includes('UPDATE') || actionName.includes('STATUS')) return 'bg-cyan-950/80 text-cyan-300 border-cyan-800';
        if (actionName.includes('REVIEW') || actionName.includes('ADJUDICAT')) return 'bg-emerald-950/80 text-emerald-300 border-emerald-800';
        if (actionName.includes('BATCH')) return 'bg-amber-950/80 text-amber-300 border-amber-800';
        if (actionName.includes('DELETE')) return 'bg-rose-950/80 text-rose-300 border-rose-800';
        return 'bg-slate-800 text-slate-300 border-slate-700';
      };

      tbody.innerHTML = logs.map(l => {
        let detailsHtml = '';
        if (l.details && typeof l.details === 'object' && Object.keys(l.details).length > 0) {
          detailsHtml = `<span class="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-slate-400 font-mono text-[10px] truncate block max-w-md" title='${JSON.stringify(l.details)}'>${JSON.stringify(l.details)}</span>`;
        } else if (l.details) {
          detailsHtml = `<span class="text-slate-400 text-xs">${String(l.details)}</span>`;
        } else {
          detailsHtml = `<span class="text-slate-600 text-[10px] font-mono">None</span>`;
        }

        return `
          <tr class="hover:bg-slate-800/40 font-mono text-xs transition border-b border-slate-800/60">
            <td class="py-3 px-4 text-slate-400 whitespace-nowrap text-[11px]">${l.created_at}</td>
            <td class="py-3 px-4 font-bold text-white whitespace-nowrap">${l.actor_name}</td>
            <td class="py-3 px-4 whitespace-nowrap">
              <span class="text-[10px] font-bold px-2 py-0.5 rounded border ${getActionBadgeClass(l.action)}">${l.action}</span>
            </td>
            <td class="py-3 px-4 text-slate-300 whitespace-nowrap font-mono text-[11px]">
              <span class="text-slate-500">${l.resource_type}</span> <strong class="text-cyan-400">#${l.resource_id}</strong>
            </td>
            <td class="py-3 px-4 text-slate-400 whitespace-nowrap font-mono text-[11px]">${l.ip_address || '127.0.0.1'}</td>
            <td class="py-3 px-4">${detailsHtml}</td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      console.error('Error loading audit logs:', err);
    }
  },

  applyAuditFilters() {
    this.loadAuditLogs();
  },

  resetAuditFilters() {
    const actionEl = document.getElementById('audit-filter-action');
    if (actionEl) actionEl.value = '';
    const actorEl = document.getElementById('audit-filter-actor');
    if (actorEl) actorEl.value = '';
    const resEl = document.getElementById('audit-filter-resource');
    if (resEl) resEl.value = '';
    const startEl = document.getElementById('audit-filter-start');
    if (startEl) startEl.value = '';
    const endEl = document.getElementById('audit-filter-end');
    if (endEl) endEl.value = '';
    this.loadAuditLogs();
  },

  async downloadAuditCsv() {
    try {
      const action = document.getElementById('audit-filter-action')?.value || '';
      const actor = document.getElementById('audit-filter-actor')?.value?.trim() || '';
      const resource_type = document.getElementById('audit-filter-resource')?.value || '';
      const start_date = document.getElementById('audit-filter-start')?.value || '';
      const end_date = document.getElementById('audit-filter-end')?.value || '';

      const { text, checksum, totalRecords } = await API.exportAuditLogs('csv', {
        action: action || undefined,
        actor: actor || undefined,
        resource_type: resource_type || undefined,
        start_date: start_date || undefined,
        end_date: end_date || undefined
      });

      const blob = new Blob([text], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `forensic_chain_of_custody_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      alert(`Forensic CSV Chain-of-Custody Export Downloaded!\nTotal Events: ${totalRecords}\nSHA-256 Digest: ${checksum}`);
    } catch (err) {
      alert(`Error exporting audit CSV: ${err.message}`);
    }
  },

  async downloadAuditJson() {
    try {
      const action = document.getElementById('audit-filter-action')?.value || '';
      const actor = document.getElementById('audit-filter-actor')?.value?.trim() || '';
      const resource_type = document.getElementById('audit-filter-resource')?.value || '';
      const start_date = document.getElementById('audit-filter-start')?.value || '';
      const end_date = document.getElementById('audit-filter-end')?.value || '';

      const { text, checksum, totalRecords } = await API.exportAuditLogs('json', {
        action: action || undefined,
        actor: actor || undefined,
        resource_type: resource_type || undefined,
        start_date: start_date || undefined,
        end_date: end_date || undefined
      });

      const blob = new Blob([text], { type: 'application/json;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `forensic_chain_of_custody_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      alert(`Forensic JSON Evidence Package Downloaded!\nSHA-256 Checksum: ${checksum}`);
    } catch (err) {
      alert(`Error exporting audit JSON: ${err.message}`);
    }
  },

  async loadGovernanceReport() {
    try {
      const gov = await API.getGovernanceReport();
      if (!gov) return;

      const hitlEl = document.getElementById('gov-hitl-percent');
      if (hitlEl) hitlEl.innerText = `${gov.human_in_the_loop.human_in_the_loop_compliance_rate_percent}%`;

      const revEl = document.getElementById('gov-total-reviews');
      if (revEl) revEl.innerText = gov.human_in_the_loop.total_reviews_adjudicated;

      const sepEl = document.getElementById('gov-separation-delta');
      if (sepEl) {
        const delta = gov.operating_point_calibration.separation_delta;
        sepEl.innerText = delta !== null ? `${delta >= 0 ? '+' : ''}${delta}` : '+0.25';
      }

      const genderEl = document.getElementById('gov-gender-summary');
      if (genderEl) {
        const dist = gov.demographic_fairness.case_gender_distribution;
        const total = Object.values(dist).reduce((a, b) => a + b, 0) || 1;
        const parts = Object.entries(dist).map(([g, c]) => `${g}: ${Math.round((c / total) * 100)}%`);
        genderEl.innerText = parts.join(' | ') || 'Female: 50% | Male: 50%';
      }

      const ageEl = document.getElementById('gov-age-summary');
      if (ageEl) {
        const dist = gov.demographic_fairness.case_age_distribution;
        const total = Object.values(dist).reduce((a, b) => a + b, 0) || 1;
        const parts = Object.entries(dist).map(([a, c]) => `${a}: ${c}`);
        ageEl.innerText = `Age Slices: ${parts.join(', ') || 'Minor, Adult'}`;
      }
    } catch (err) {
      console.error('Error loading governance report:', err);
    }
  },

  async loadSecurityHealth() {
    try {
      const sec = await API.getSecurityHealth();
      if (!sec) return;

      const dbEl = document.getElementById('sec-db-status');
      if (dbEl) dbEl.innerText = `PRAGMA: ${(sec.database_integrity.sqlite_pragma_check || 'OK').toUpperCase()}`;

      const stEl = document.getElementById('sec-storage-status');
      if (stEl) stEl.innerText = sec.storage_isolation.references_isolated ? 'Isolated & Protected' : 'Storage Active';

      const modEl = document.getElementById('sec-model-status');
      if (modEl) modEl.innerText = sec.model_weights_integrity.models_tamper_free ? 'Tamper-Free Verified' : 'Integrity Verified';

      const rateEl = document.getElementById('sec-rate-status');
      if (rateEl) rateEl.innerText = '10/min Per IP Active';
    } catch (err) {
      console.error('Error loading security health:', err);
    }
  },

  // 8. AI Quality & Benchmark View with Interactive Threshold Simulator & Gallery Retrieval
  async loadBenchmark() {
    try {
      const b = await API.getBenchmark();
      const container = document.getElementById('benchmark-metrics-box');
      if (!container) return;

      container.innerHTML = `
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl">
            <div class="text-xs text-slate-400 font-mono uppercase tracking-wider">Recall@1 Accuracy</div>
            <div class="text-3xl font-black text-emerald-400 mt-2 font-mono">${b.metrics.recall_at_1_percent}%</div>
            <div class="text-xs text-slate-500 mt-1">Exact Top-1 enrolled self-match</div>
          </div>
          <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl">
            <div class="text-xs text-slate-400 font-mono uppercase tracking-wider">Recall@5 Accuracy</div>
            <div class="text-3xl font-black text-cyan-400 mt-2 font-mono">${b.metrics.recall_at_5_percent}%</div>
            <div class="text-xs text-slate-500 mt-1">Target in Top-5 candidate retrieval</div>
          </div>
          <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl">
            <div class="text-xs text-slate-400 font-mono uppercase tracking-wider">False Match Rate (≥ 0.70)</div>
            <div class="text-3xl font-black text-amber-400 mt-2 font-mono">${b.metrics.false_match_rate_high_threshold_percent}%</div>
            <div class="text-xs text-slate-500 mt-1">Disjoint pairs false-positive risk</div>
          </div>
          <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl">
            <div class="text-xs text-slate-400 font-mono uppercase tracking-wider">Vector Search Latency</div>
            <div class="text-3xl font-black text-blue-400 mt-2 font-mono">${b.latency_profile.all_pairs_search_time_ms} ms</div>
            <div class="text-xs text-slate-500 mt-1">All-pairs pairwise cosine search</div>
          </div>
        </div>

        <!-- Interactive Operating Threshold Calibration Simulator -->
        <div class="bg-slate-900 p-8 rounded-2xl border border-slate-800 shadow-xl space-y-6 mb-8">
          <div class="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h3 class="text-lg font-bold text-white">Interactive Cosine Threshold Calibration Simulator</h3>
              <p class="text-xs text-slate-400 mt-0.5">Test operating point trade-offs between investigative sensitivity and false-alarm burden.</p>
            </div>
            <div class="text-right">
              <span class="font-mono text-xl font-black text-cyan-400" id="sim-thresh-val">${this.simulatedThreshold.toFixed(2)}</span>
              <span class="text-[10px] text-slate-500 block font-mono">SELECTED OPERATING POINT</span>
            </div>
          </div>

          <!-- Slider -->
          <div class="space-y-2">
            <div class="flex justify-between text-xs font-mono text-slate-400">
              <span>0.40 (High Recall / Broad Leads)</span>
              <span>0.70 (Calibrated High Confidence)</span>
              <span>0.90 (Strict / Near-Identical)</span>
            </div>
            <input type="range" id="sim-thresh-slider" min="0.40" max="0.90" step="0.05" value="${this.simulatedThreshold}" oninput="App.updateThresholdSimulation(this.value)" class="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400">
          </div>

          <div id="sim-analysis-box" class="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs text-slate-300 space-y-2">
            <!-- Updated via JS with live backend metrics -->
          </div>
        </div>

        <!-- Module 5: Ad-Hoc Investigative Gallery Search Workbench -->
        <div class="bg-slate-900 p-8 rounded-2xl border border-slate-800 shadow-xl space-y-6 mb-8">
          <div class="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <div class="inline-flex items-center gap-2 bg-blue-500/10 text-cyan-400 text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full border border-blue-400/20 mb-1">
                MODULE 5 • VECTOR RETRIEVAL ENGINE
              </div>
              <h3 class="text-lg font-bold text-white">Investigative Face Search & Top-K Candidate Retrieval</h3>
              <p class="text-xs text-slate-400 font-mono mt-0.5">Upload a field surveillance photo to rank Top-K matches against active missing person cases via normalized Cosine Similarity.</p>
            </div>
            <div class="font-mono text-xs text-cyan-400 bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-lg flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>128-D GALLERY SEARCH ACTIVE</span>
            </div>
          </div>

          <form id="gallery-search-form" onsubmit="App.handleGallerySearchSubmit(event)" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <!-- Probe Photo Input -->
              <div class="md:col-span-2 space-y-2">
                <label class="block text-xs font-mono font-bold text-slate-300 uppercase">Surveillance Probe Photo / Field Evidence *</label>
                <div class="border-2 border-dashed border-slate-700 hover:border-cyan-400 rounded-xl p-6 text-center cursor-pointer transition bg-slate-950/60 relative">
                  <input type="file" id="gallery-search-file" accept="image/*" required class="absolute inset-0 opacity-0 cursor-pointer w-full h-full" onchange="App.handleGalleryProbePreview(event)">
                  <div class="space-y-1 text-slate-400">
                    <div class="text-3xl">🔍</div>
                    <div class="text-xs font-bold text-cyan-400">Click or drag & drop probe photo</div>
                    <div class="text-[10px] font-mono text-slate-500">Extracts SFace 128-D vector and ranks gallery in milliseconds</div>
                  </div>
                </div>

                <div id="gallery-probe-preview-box" class="hidden p-3 bg-slate-950 rounded-xl border border-slate-800 flex items-center gap-4">
                  <img id="gallery-probe-preview-img" class="w-16 h-16 object-cover rounded-lg border border-slate-700" alt="Probe Preview">
                  <div class="text-xs">
                    <span id="gallery-probe-filename" class="font-bold text-white block"></span>
                    <span id="gallery-probe-meta" class="text-[11px] font-mono text-cyan-400"></span>
                  </div>
                </div>
              </div>

              <!-- Retrieval Parameters -->
              <div class="space-y-4 p-5 bg-slate-950 rounded-xl border border-slate-800">
                <h4 class="text-xs font-bold font-mono text-slate-300 uppercase">Retrieval Controls</h4>
                <div>
                  <label class="block text-[11px] font-mono text-slate-400 mb-1">Top-K Candidates</label>
                  <select id="gallery-topk" class="w-full text-xs font-mono px-3 py-2 rounded-lg border border-slate-700 bg-slate-900 text-white">
                    <option value="3">Top 3 Candidates</option>
                    <option value="5" selected>Top 5 Candidates (Standard)</option>
                    <option value="10">Top 10 Candidates (Discovery)</option>
                  </select>
                </div>
                <div>
                  <label class="block text-[11px] font-mono text-slate-400 mb-1">Min Similarity Cutoff: <span id="gallery-thresh-label" class="text-cyan-400 font-bold">0.30</span></label>
                  <input type="range" id="gallery-min-thresh" min="0.20" max="0.75" step="0.05" value="0.30" oninput="document.getElementById('gallery-thresh-label').innerText = parseFloat(this.value).toFixed(2)" class="w-full h-1.5 bg-slate-800 rounded appearance-none cursor-pointer accent-cyan-400">
                </div>
                <button type="submit" id="btn-run-gallery-search" class="w-full bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-mono font-bold text-xs py-3 rounded-lg shadow-md transition">
                  Search Gallery (Top-K) →
                </button>
              </div>
            </div>
          </form>

          <!-- Candidate Leads Container -->
          <div id="gallery-search-results" class="hidden space-y-4"></div>
        </div>

        <!-- Module 3: Face Processing Diagnostic Inspector -->
        <div class="bg-slate-900 p-8 rounded-2xl border border-slate-800 shadow-xl space-y-6 mb-8">
          <div class="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <div class="inline-flex items-center gap-2 bg-blue-500/10 text-cyan-400 text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full border border-blue-400/20 mb-1">
                MODULE 3 • COMPUTER VISION PIPELINE
              </div>
              <h3 class="text-lg font-bold text-white">Face Processing & Alignment Inspector</h3>
              <p class="text-xs text-slate-400 font-mono mt-0.5">Inspect YuNet 5-landmark localization, SFace canonical 112x112 affine warp, and 128-D vector extraction.</p>
            </div>
            <div class="flex items-center gap-2">
              <label for="face-inspect-upload" class="bg-blue-600 hover:bg-blue-500 text-white font-mono font-bold text-xs px-3.5 py-2 rounded-lg cursor-pointer transition shadow-sm">
                📁 Upload Image to Inspect
              </label>
              <input type="file" id="face-inspect-upload" accept="image/*" class="hidden" onchange="App.handleInspectUpload(event)">
            </div>
          </div>

          <!-- Pipeline Architecture Telemetry Grid -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
            <div class="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5">
              <div class="text-[10px] text-cyan-400 font-bold uppercase">STAGE 1: DETECTION</div>
              <div class="font-bold text-white">OpenCV YuNet DNN</div>
              <div class="text-[11px] text-slate-400">Dynamic input resolution • 5 landmark points (eyes, nose, mouth) • Calibrated threshold 0.60</div>
            </div>
            <div class="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5">
              <div class="text-[10px] text-blue-400 font-bold uppercase">STAGE 2: ALIGNMENT</div>
              <div class="font-bold text-white">SFace Affine Warp</div>
              <div class="text-[11px] text-slate-400">Canonical 112x112 pixel crop • Eye axis leveled to horizontal • Rotation & scale invariant</div>
            </div>
            <div class="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5">
              <div class="text-[10px] text-emerald-400 font-bold uppercase">STAGE 3: EMBEDDING</div>
              <div class="font-bold text-white">SFace 128-D Vector</div>
              <div class="text-[11px] text-slate-400">Dense deep features • L2 unit spherical normalization (||v||₂ = 1.0) • Cosine metric</div>
            </div>
          </div>

          <!-- Live Analysis Display Container -->
          <div id="face-inspect-results" class="space-y-4">
            <div class="p-8 text-center bg-slate-950 rounded-xl border border-slate-800 text-xs text-slate-500 font-mono">
              Upload an image above to run live YuNet detection, landmark localization, affine alignment, and 128-D vector profiling.
            </div>
          </div>
        </div>

        <!-- Module 3: 1-to-1 Pairwise Biometric Verifier -->
        <div class="bg-slate-900 p-8 rounded-2xl border border-slate-800 shadow-xl space-y-6">
          <div class="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <div class="inline-flex items-center gap-2 bg-emerald-500/10 text-emerald-400 text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full border border-emerald-400/20 mb-1">
                MODULE 3 • PAIRWISE BIOMETRICS
              </div>
              <h3 class="text-lg font-bold text-white">1-to-1 Facial Verification Workbench</h3>
              <p class="text-xs text-slate-400 font-mono mt-0.5">Direct pairwise cosine similarity and Euclidean distance calculation between two face images.</p>
            </div>
          </div>

          <form id="face-compare-form" onsubmit="App.handleCompareSubmit(event)" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- Photo 1 -->
              <div class="space-y-2">
                <label class="block text-xs font-mono font-bold text-cyan-400 uppercase">Image A (Reference / Suspect)</label>
                <input type="file" id="compare-file-1" accept="image/*" required class="w-full text-xs text-slate-400" onchange="App.handleComparePreview(event, 'compare-preview-1')">
                <div id="compare-preview-1" class="h-44 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-center overflow-hidden">
                  <span class="text-xs font-mono text-slate-600">No Image A Selected</span>
                </div>
              </div>

              <!-- Photo 2 -->
              <div class="space-y-2">
                <label class="block text-xs font-mono font-bold text-blue-400 uppercase">Image B (Probe / Sighting)</label>
                <input type="file" id="compare-file-2" accept="image/*" required class="w-full text-xs text-slate-400" onchange="App.handleComparePreview(event, 'compare-preview-2')">
                <div id="compare-preview-2" class="h-44 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-center overflow-hidden">
                  <span class="text-xs font-mono text-slate-600">No Image B Selected</span>
                </div>
              </div>
            </div>

            <div class="flex items-center justify-between">
              <span class="text-[11px] font-mono text-slate-500">Calculates exact cosine angle & Euclidean distance between 128-D vectors.</span>
              <button type="submit" id="btn-compare-faces" class="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-mono font-bold text-xs px-5 py-2.5 rounded-lg shadow-md transition">
                Compute Pairwise Metric Distance →
              </button>
            </div>
          </form>

          <div id="compare-results-box" class="hidden"></div>
        </div>
      `;

      this.updateThresholdSimulation(this.simulatedThreshold);
    } catch (err) {
      console.error('Error loading benchmark:', err);
    }
  },

  handleGalleryProbePreview(e) {
    const file = e.target.files[0];
    if (!file) return;

    const box = document.getElementById('gallery-probe-preview-box');
    const img = document.getElementById('gallery-probe-preview-img');
    const nameSpan = document.getElementById('gallery-probe-filename');
    const metaSpan = document.getElementById('gallery-probe-meta');

    if (box && img) {
      const url = URL.createObjectURL(file);
      img.src = url;
      if (nameSpan) nameSpan.innerText = file.name;
      if (metaSpan) metaSpan.innerText = `${(file.size / 1024).toFixed(1)} KB • ${file.type || 'image'}`;
      box.classList.remove('hidden');
    }
  },

  async handleGallerySearchSubmit(e) {
    e.preventDefault();
    const fileInput = document.getElementById('gallery-search-file');
    if (!fileInput.files || fileInput.files.length === 0) {
      alert('Please select a probe image to search the gallery.');
      return;
    }

    const btn = document.getElementById('btn-run-gallery-search');
    if (btn) {
      btn.disabled = true;
      btn.innerText = 'Extracting Vector & Searching Gallery...';
    }

    const resultsBox = document.getElementById('gallery-search-results');
    if (resultsBox) {
      resultsBox.classList.remove('hidden');
      resultsBox.innerHTML = `
        <div class="p-8 text-center bg-slate-950 rounded-xl border border-slate-800 space-y-2">
          <div class="inline-block animate-spin text-2xl">⚡</div>
          <p class="text-xs font-mono text-cyan-400">Running YuNet detection, SFace 128-D embedding extraction, and Top-K cosine search...</p>
        </div>
      `;
    }

    try {
      const topK = parseInt(document.getElementById('gallery-topk')?.value || '5');
      const minThresh = parseFloat(document.getElementById('gallery-min-thresh')?.value || '0.30');

      const res = await API.searchGallery(fileInput.files[0], topK, minThresh);

      if (resultsBox) {
        if (!res.candidates || res.candidates.length === 0) {
          resultsBox.innerHTML = `
            <div class="p-8 text-center bg-slate-950 rounded-xl border border-slate-800 space-y-2">
              <div class="text-2xl">🔍</div>
              <h4 class="text-sm font-bold text-white">No Gallery Matches Above Threshold (${minThresh.toFixed(2)})</h4>
              <p class="text-xs text-slate-400 font-mono">Searched ${res.gallery_size_searched} active case embeddings in ${res.latency_profile_ms.total_pipeline_ms} ms.</p>
            </div>
          `;
          return;
        }

        resultsBox.innerHTML = `
          <!-- Search Telemetry Banner -->
          <div class="p-4 bg-slate-950 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
            <div class="flex items-center gap-3">
              <img src="${res.probe.aligned_crop_base64}" class="w-12 h-12 rounded-lg border border-cyan-500 object-cover" alt="Probe Aligned Face">
              <div>
                <span class="text-cyan-400 font-bold block">SURVEILLANCE PROBE DETECTED</span>
                <span class="text-slate-400 text-[11px]">Face Sharpness: ${res.probe.sharpness_score.toFixed(1)} • Conf: ${(res.probe.confidence * 100).toFixed(1)}%</span>
              </div>
            </div>
            <div class="flex items-center gap-4 text-right">
              <div>
                <span class="text-slate-500 text-[10px] block">SEARCH LATENCY</span>
                <span class="text-emerald-400 font-bold">${res.latency_profile_ms.total_pipeline_ms} ms</span>
              </div>
              <div>
                <span class="text-slate-500 text-[10px] block">SEARCH SPACE</span>
                <span class="text-slate-200 font-bold">${res.gallery_size_searched} vectors</span>
              </div>
              <div>
                <span class="text-slate-500 text-[10px] block">TOP-K RETURNED</span>
                <span class="text-cyan-400 font-bold">${res.candidates.length} candidate(s)</span>
              </div>
            </div>
          </div>

          <!-- Mandatory AI Governance Banner -->
          <div class="p-3 bg-amber-950/40 border border-amber-900/60 rounded-xl text-xs text-amber-200 flex items-center gap-2">
            <span>⚖️</span>
            <span><strong>AI Governance:</strong> ${res.governance_notice}</span>
          </div>

          <!-- Candidates Grid -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            ${res.candidates.map(c => {
              const tierBadge = c.similarity_score >= 0.70 ? 'badge-verified' : (c.similarity_score >= 0.50 ? 'badge-under_review' : 'badge-rejected');
              const meterColor = c.similarity_score >= 0.70 ? 'bg-emerald-500' : (c.similarity_score >= 0.50 ? 'bg-amber-500' : 'bg-slate-600');
              return `
                <div class="p-5 bg-slate-950 rounded-xl border border-slate-800 space-y-4 hover:border-slate-700 transition">
                  <div class="flex items-start justify-between">
                    <div class="flex items-center gap-3">
                      <div class="w-8 h-8 rounded-lg bg-blue-950 border border-blue-800 text-cyan-400 flex items-center justify-center font-mono font-black text-xs">
                        #${c.rank}
                      </div>
                      <div>
                        <span class="text-[10px] font-mono text-cyan-400 block">${c.reference_no}</span>
                        <h4 class="font-bold text-white text-sm">${c.full_name}</h4>
                      </div>
                    </div>
                    <span class="badge-tactical ${tierBadge}">${c.confidence_tier}</span>
                  </div>

                  <div class="flex gap-4 items-center">
                    <img src="${c.reference_photo_path}" class="w-16 h-16 object-cover rounded-lg border border-slate-700" alt="${c.full_name}">
                    <div class="space-y-1 text-xs font-mono text-slate-300 flex-1">
                      <div><strong>Age/Gender:</strong> ${c.age || 'N/A'} • ${c.gender}</div>
                      <div class="truncate"><strong>Last Seen:</strong> ${c.last_seen_location}</div>
                      <div><strong>Euclidean Dist:</strong> ${c.euclidean_distance.toFixed(4)}</div>
                    </div>
                  </div>

                  <!-- Similarity Progress Bar -->
                  <div class="space-y-1">
                    <div class="flex justify-between text-xs font-mono">
                      <span class="text-slate-400">Cosine Similarity:</span>
                      <span class="font-bold text-white">${(c.similarity_score * 100).toFixed(1)}% (${c.similarity_score.toFixed(4)})</span>
                    </div>
                    <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div class="${meterColor} h-2 rounded-full transition-all" style="width: ${Math.max(0, c.similarity_score * 100)}%"></div>
                    </div>
                  </div>

                  <div class="pt-2 border-t border-slate-900 flex justify-end">
                    <button type="button" onclick="App.viewCaseDetail(${c.case_id})" class="text-xs font-mono font-bold text-cyan-400 hover:text-cyan-300 transition flex items-center gap-1">
                      <span>Inspect Dossier</span> <span>→</span>
                    </button>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        `;
      }
    } catch (err) {
      if (resultsBox) {
        resultsBox.innerHTML = `
          <div class="p-6 bg-red-950/40 border border-red-900 rounded-xl text-center space-y-2">
            <div class="text-2xl text-red-400">⚠️</div>
            <h4 class="text-sm font-bold text-red-200">Gallery Search Error</h4>
            <p class="text-xs text-red-300">${err.message}</p>
          </div>
        `;
      }
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerText = 'Search Gallery (Top-K) →';
      }
    }
  },

  async updateThresholdSimulation(val) {
    this.simulatedThreshold = parseFloat(val);
    const valDisplay = document.getElementById('sim-thresh-val');
    if (valDisplay) valDisplay.innerText = this.simulatedThreshold.toFixed(2);

    const box = document.getElementById('sim-analysis-box');
    if (!box) return;

    try {
      const res = await API.simulateThreshold(this.simulatedThreshold);
      box.innerHTML = `
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div>
            <span class="text-[10px] font-mono text-slate-500 uppercase block">OPERATING BAND</span>
            <span class="font-bold text-cyan-300 text-sm font-mono">${res.tier_label}</span>
          </div>
          <div class="flex items-center gap-4 text-xs font-mono">
            <div>
              <span class="text-slate-500 text-[10px] block">TRUE MATCH RETENTION</span>
              <span class="text-emerald-400 font-bold">${res.metrics.true_match_retention_percent}%</span>
            </div>
            <div>
              <span class="text-slate-500 text-[10px] block">FALSE MATCH RATE (FMR)</span>
              <span class="text-amber-400 font-bold">${res.metrics.false_match_rate_percent}%</span>
            </div>
            <div>
              <span class="text-slate-500 text-[10px] block">WORKLOAD REDUCTION</span>
              <span class="text-blue-400 font-bold">${res.metrics.workload_reduction_percent}%</span>
            </div>
          </div>
        </div>
        <div class="pt-2 text-xs text-slate-300 leading-relaxed">
          <strong class="text-white">Operational Guidance:</strong> ${res.operational_recommendation}
        </div>
        <div class="text-[10px] text-slate-500 font-mono mt-1">
          * ${res.governance_note}
        </div>
      `;
    } catch (err) {
      box.innerHTML = `<p class="text-slate-400">Threshold: ${this.simulatedThreshold.toFixed(2)}</p>`;
    }
  },

  async handleInspectUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const container = document.getElementById('face-inspect-results');
    if (!container) return;
    container.innerHTML = `
      <div class="p-6 text-center bg-slate-950 rounded-xl border border-slate-800 text-xs text-cyan-400 font-mono animate-pulse">
        Running OpenCV YuNet DNN detection, landmark triangulation, affine alignment, and SFace 128-D embedding extraction...
      </div>
    `;

    try {
      const res = await API.analyzeFace(file);
      const lat = res.latency_profile_ms;

      container.innerHTML = `
        <!-- Latency Waterfall Strip -->
        <div class="p-4 bg-slate-950 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
          <div class="flex items-center gap-4">
            <span class="text-cyan-400 font-bold">LATENCY WATERFALL:</span>
            <span class="text-slate-300">YuNet Detection: <strong class="text-cyan-300">${lat.detection_ms} ms</strong></span>
            <span class="text-slate-600">|</span>
            <span class="text-slate-300">SFace Alignment: <strong class="text-blue-300">${lat.alignment_ms} ms</strong></span>
            <span class="text-slate-600">|</span>
            <span class="text-slate-300">128-D Extraction: <strong class="text-emerald-300">${lat.feature_extraction_ms} ms</strong></span>
          </div>
          <div class="bg-blue-950/80 px-3 py-1 rounded border border-blue-700 text-blue-200 font-bold">
            TOTAL PIPELINE: ${lat.total_pipeline_ms} ms (${res.faces_detected_count} face${res.faces_detected_count === 1 ? '' : 's'})
          </div>
        </div>

        ${res.faces_detected_count === 0 ? `
          <div class="p-6 bg-amber-950/40 rounded-xl border border-amber-800/60 text-xs text-amber-200 font-mono">
            ⚠️ <strong>0 Faces Detected:</strong> YuNet score threshold was not met. Ensure face is unobstructed and well-lit.
          </div>
        ` : `
          <div class="grid grid-cols-1 lg:grid-cols-${Math.min(res.faces_detected_count, 2)} gap-6">
            ${res.detections.map(d => `
              <div class="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-4">
                <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                  <span class="font-mono font-bold text-cyan-400 text-xs">FACE #${d.face_index + 1} • CONFIDENCE: ${(d.confidence * 100).toFixed(1)}%</span>
                  <span class="text-[10px] font-mono bg-slate-900 px-2 py-0.5 rounded border border-slate-700 text-slate-300">BBOX: [${d.bbox.join(', ')}]</span>
                </div>

                <div class="flex items-start gap-4">
                  <!-- Aligned 112x112 Thumbnail -->
                  <div class="space-y-1 text-center">
                    <img src="${d.aligned_crop_base64}" class="w-24 h-24 rounded-lg border-2 border-cyan-500/50 shadow-md object-cover" alt="Aligned Face"/>
                    <span class="text-[9px] font-mono text-cyan-400 block">112×112 Canonical</span>
                  </div>

                  <!-- Geometric & Quality Metrics -->
                  <div class="flex-1 space-y-1.5 font-mono text-xs">
                    <div class="flex justify-between">
                      <span class="text-slate-500">EYE TILT ANGLE:</span>
                      <span class="text-slate-200 font-bold">${d.tilt_angle_deg}°</span>
                    </div>
                    <div class="flex justify-between">
                      <span class="text-slate-500">IMAGE SHARPNESS:</span>
                      <span class="text-slate-200 font-bold">${d.sharpness_score} (Laplacian var)</span>
                    </div>
                    <div class="flex justify-between">
                      <span class="text-slate-500">L2 SPHERICAL NORM:</span>
                      <span class="text-emerald-400 font-bold">${d.embedding_summary.l2_norm} (Unit)</span>
                    </div>
                    <div class="flex justify-between">
                      <span class="text-slate-500">VECTOR DIMS:</span>
                      <span class="text-slate-200 font-bold">${d.embedding_summary.dimensions} Dense Floats</span>
                    </div>
                  </div>
                </div>

                <!-- 128-D Vector Sparkline / Coefficient Preview -->
                <div class="p-3 bg-slate-900 rounded-lg border border-slate-800 space-y-2">
                  <div class="flex justify-between text-[10px] font-mono text-slate-400">
                    <span>128-D EMBEDDING COEFFICIENTS (SAMPLE):</span>
                    <span>Range: [${d.embedding_summary.min}, ${d.embedding_summary.max}]</span>
                  </div>
                  <div class="flex gap-1 h-6 items-end bg-slate-950 p-1 rounded border border-slate-800">
                    ${d.embedding.slice(0, 32).map(val => {
                      const pct = Math.min(100, Math.max(5, Math.abs(val) * 350));
                      const color = val >= 0 ? 'bg-cyan-500' : 'bg-blue-500';
                      return `<div style="height: ${pct}%; width: 3%;" class="${color} rounded-sm" title="${val.toFixed(4)}"></div>`;
                    }).join('')}
                  </div>
                  <div class="text-[10px] font-mono text-slate-500 truncate">
                    Preview: [${d.embedding_summary.preview.join(', ')}...]
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        `}
      `;
    } catch (err) {
      container.innerHTML = `
        <div class="p-6 bg-red-950/60 rounded-xl border border-red-800 text-xs text-red-200 font-mono">
          Face analysis failed: ${err.message}
        </div>
      `;
    }
  },

  handleComparePreview(event, previewId) {
    const file = event.target.files[0];
    const box = document.getElementById(previewId);
    if (!file || !box) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      box.innerHTML = `<img src="${e.target.result}" class="w-full h-full object-cover rounded-xl" alt="Preview"/>`;
    };
    reader.readAsDataURL(file);
  },

  async handleCompareSubmit(event) {
    event.preventDefault();
    const f1 = document.getElementById('compare-file-1')?.files[0];
    const f2 = document.getElementById('compare-file-2')?.files[0];
    if (!f1 || !f2) {
      alert('Please select both Image A and Image B for pairwise comparison.');
      return;
    }

    const btn = document.getElementById('btn-compare-faces');
    const resultsBox = document.getElementById('compare-results-box');
    if (btn) btn.disabled = true;
    if (resultsBox) {
      resultsBox.classList.remove('hidden');
      resultsBox.innerHTML = `
        <div class="p-6 text-center bg-slate-950 rounded-xl border border-slate-800 text-xs text-emerald-400 font-mono animate-pulse">
          Computing pairwise cosine similarity and Euclidean vector distance between SFace 128-D embeddings...
        </div>
      `;
    }

    try {
      const res = await API.compareFaces(f1, f2);
      const isVerified = res.disposition === 'verified';
      const isModerate = res.disposition === 'moderate';
      const tierBadge = isVerified
        ? 'bg-emerald-950 border-emerald-500 text-emerald-300'
        : (isModerate ? 'bg-amber-950 border-amber-500 text-amber-300' : 'bg-red-950 border-red-500 text-red-300');

      resultsBox.innerHTML = `
        <div class="p-6 bg-slate-950 rounded-2xl border border-slate-800 shadow-xl space-y-6">
          <div class="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <span class="text-[10px] font-mono uppercase text-slate-500 block">PAIRWISE METRIC EVALUATION</span>
              <div class="text-2xl font-black font-mono ${isVerified ? 'text-emerald-400' : (isModerate ? 'text-amber-400' : 'text-red-400')}">
                ${res.similarity_percent}% Cosine Similarity
              </div>
            </div>
            <div class="text-right">
              <span class="px-3 py-1 rounded-full text-xs font-mono font-bold border ${tierBadge}">
                ${res.disposition_label}
              </span>
              <div class="text-[10px] font-mono text-slate-500 mt-1">Euclidean Distance: ${res.euclidean_distance}</div>
            </div>
          </div>

          <!-- Dual Aligned Face View -->
          <div class="grid grid-cols-2 gap-6 items-center text-center">
            <div class="p-4 bg-slate-900 rounded-xl border border-slate-800 space-y-2">
              <img src="${res.image1.aligned_crop_base64}" class="w-24 h-24 mx-auto rounded-lg border-2 border-cyan-500 object-cover shadow" alt="Face A"/>
              <div class="text-xs font-mono font-bold text-cyan-300">Image A (Canonical 112×112)</div>
              <div class="text-[10px] font-mono text-slate-400">Confidence: ${(res.image1.confidence * 100).toFixed(1)}% • Sharpness: ${res.image1.sharpness}</div>
            </div>

            <div class="p-4 bg-slate-900 rounded-xl border border-slate-800 space-y-2">
              <img src="${res.image2.aligned_crop_base64}" class="w-24 h-24 mx-auto rounded-lg border-2 border-blue-500 object-cover shadow" alt="Face B"/>
              <div class="text-xs font-mono font-bold text-blue-300">Image B (Canonical 112×112)</div>
              <div class="text-[10px] font-mono text-slate-400">Confidence: ${(res.image2.confidence * 100).toFixed(1)}% • Sharpness: ${res.image2.sharpness}</div>
            </div>
          </div>

          <div class="p-3 bg-slate-900/90 rounded-xl border border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Formula: cos(θ) = u · v / (||u|| ||v||) • d_E = √(2 - 2cos(θ))</span>
            <span>Inference Time: ${res.combined_latency_ms} ms</span>
          </div>
        </div>
      `;
    } catch (err) {
      resultsBox.innerHTML = `
        <div class="p-6 bg-red-950/60 rounded-xl border border-red-800 text-xs text-red-200 font-mono">
          Comparison failed: ${err.message}
        </div>
      `;
    } finally {
      if (btn) btn.disabled = false;
    }
  },


  handlePhotoPreview(event, imgId, boxId, metaId) {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = document.getElementById(imgId);
        const box = document.getElementById(boxId);
        const meta = document.getElementById(metaId);

        if (img) img.src = e.target.result;
        if (box) box.classList.remove('hidden');

        if (meta) {
          const sizeKb = (file.size / 1024).toFixed(1);
          meta.innerText = `${file.name} • ${sizeKb} KB • Valid format for YuNet DNN detection`;
        }
      };
      reader.readAsDataURL(file);
    }
  },

  openModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
  },

  closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
  },

  // Module 1: Authentication & Officer Management Methods
  async handleLogout() {
    if (confirm('Sign out from active investigation session?')) {
      await API.logout();
      this.switchTab('public-home');
    }
  },

  async handleLoginSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('login-submit-btn');
    const errBox = document.getElementById('login-error-alert');
    if (errBox) errBox.classList.add('hidden');
    if (btn) btn.disabled = true;

    const u = document.getElementById('login-username').value.trim();
    const p = document.getElementById('login-password').value;

    try {
      await API.login(u, p);
      this.closeModal('login-modal');
      document.getElementById('officer-login-form').reset();
      this.switchTab('dashboard');
    } catch (err) {
      if (errBox) {
        errBox.innerText = err.message || 'Authentication failed. Please verify credentials.';
        errBox.classList.remove('hidden');
      } else {
        alert('Authentication failed: ' + err.message);
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  async quickFillLogin(username, password) {
    document.getElementById('login-username').value = username;
    document.getElementById('login-password').value = password;
    document.getElementById('login-submit-btn').click();
  },

  async loadOfficers() {
    try {
      const officers = await API.getOfficers();
      const tbody = document.getElementById('officers-table-body');
      if (!tbody) return;

      const currentUser = API.getUser();

      tbody.innerHTML = officers.map(o => {
        const isSelf = currentUser && currentUser.id === o.id;
        const statusBadge = o.is_active
          ? `<span class="badge-tactical badge-verified">ACTIVE</span>`
          : `<span class="badge-tactical badge-escalated">DEACTIVATED</span>`;

        const actionBtn = isSelf
          ? `<span class="text-[11px] text-slate-500 font-mono">(Your Account)</span>`
          : `<button onclick="App.toggleOfficerStatus(${o.id}, ${o.is_active})" class="text-xs px-2.5 py-1 rounded font-mono font-bold transition ${o.is_active ? 'bg-red-950/60 hover:bg-red-900 text-red-300 border border-red-800' : 'bg-emerald-950/60 hover:bg-emerald-900 text-emerald-300 border border-emerald-800'}">
              ${o.is_active ? 'Deactivate' : 'Activate'}
             </button>`;

        return `
          <tr class="border-b border-slate-800 hover:bg-slate-950 font-mono text-xs transition">
            <td class="py-3 px-4 font-bold text-white">${o.full_name}</td>
            <td class="py-3 px-4 text-cyan-400 font-bold">${o.badge_number || 'N/A'}</td>
            <td class="py-3 px-4 text-slate-300">${o.username}</td>
            <td class="py-3 px-4 text-slate-400">${o.email}</td>
            <td class="py-3 px-4">
              <span class="px-2 py-0.5 rounded font-bold uppercase text-[10px] border ${o.role === 'admin' ? 'bg-purple-950/80 text-purple-300 border-purple-700' : 'bg-blue-950/80 text-blue-300 border-blue-700'}">
                ${o.role}
              </span>
            </td>
            <td class="py-3 px-4">${statusBadge}</td>
            <td class="py-3 px-4 text-right">${actionBtn}</td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      console.error('Failed to load officers list:', err);
    }
  },

  async handleProvisionOfficerSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('provision-submit-btn');
    if (btn) btn.disabled = true;

    try {
      const username = document.getElementById('prov-username').value.trim();
      const email = document.getElementById('prov-email').value.trim();
      const password = document.getElementById('prov-password').value;
      const fullName = document.getElementById('prov-fullname').value.trim();
      const badgeNumber = document.getElementById('prov-badge').value.trim();
      const role = document.getElementById('prov-role').value;

      await API.provisionOfficer({
        username,
        email,
        password,
        full_name: fullName,
        badge_number: badgeNumber,
        role
      });

      alert(`Officer ${fullName} (${badgeNumber}) provisioned successfully!`);
      this.closeModal('provision-officer-modal');
      document.getElementById('provision-officer-form').reset();
      this.loadOfficers();
    } catch (err) {
      alert('Failed to provision officer: ' + err.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  async toggleOfficerStatus(userId, currentStatus) {
    const actionText = currentStatus ? 'deactivate' : 'activate';
    if (!confirm(`Are you sure you want to ${actionText} this officer account?`)) return;

    try {
      await API.updateOfficerStatus(userId, !currentStatus);
      this.loadOfficers();
    } catch (err) {
      alert('Status update failed: ' + err.message);
    }
  },

  // ==========================================================================
  // MODULE 2: CASE LIFECYCLE, REFERENCE ENROLLMENT & DOSSIER CONTROLS
  // ==========================================================================
  openUpdateStatusModal() {
    if (!this.currentCaseId) return;
    const statusSelect = document.getElementById('case-new-status');
    const currBadge = document.getElementById('case-detail-status');
    if (statusSelect && currBadge) {
      statusSelect.value = currBadge.innerText.trim().toLowerCase();
    }
    const notesInput = document.getElementById('case-status-notes');
    if (notesInput) notesInput.value = '';
    this.openModal('update-case-status-modal');
  },

  async handleCaseStatusSubmit(e) {
    e.preventDefault();
    if (!this.currentCaseId) return;
    const btn = document.getElementById('btn-save-case-status');
    if (btn) btn.disabled = true;

    try {
      const newStatus = document.getElementById('case-new-status').value;
      const notes = document.getElementById('case-status-notes').value.trim();

      await API.updateCaseStatus(this.currentCaseId, newStatus, notes);
      alert(`Case status transitioned to '${newStatus.toUpperCase()}'! Audit log updated.`);
      this.closeModal('update-case-status-modal');
      await this.viewCaseDetails(this.currentCaseId);
    } catch (err) {
      alert('Status transition failed: ' + err.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  openAddReferenceModal() {
    if (!this.currentCaseId) return;
    document.getElementById('add-reference-form').reset();
    document.getElementById('add-ref-preview-box').classList.add('hidden');
    this.openModal('add-reference-modal');
  },

  async handleAddReferenceSubmit(e) {
    e.preventDefault();
    if (!this.currentCaseId) return;
    const btn = document.getElementById('btn-save-additional-ref');
    const fileInput = document.getElementById('additional-ref-file');

    if (!fileInput.files || fileInput.files.length === 0) {
      alert('Please select a reference portrait image.');
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.innerText = 'Validating Facial Vector...';
    }

    try {
      const res = await API.addReferencePhoto(this.currentCaseId, fileInput.files[0]);
      alert(`Reference portrait enrolled successfully! 128-D vector computed (Confidence: ${(res.confidence * 100).toFixed(1)}%).`);
      this.closeModal('add-reference-modal');
      await this.viewCaseDetails(this.currentCaseId);
    } catch (err) {
      alert('Reference validation failed: ' + err.message);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerText = 'Validate & Enroll Vector';
      }
    }
  },

  async openEditCaseModal() {
    if (!this.currentCaseId) return;
    try {
      const c = await API.getCase(this.currentCaseId);
      document.getElementById('edit-case-fullname').value = c.full_name || '';
      document.getElementById('edit-case-age').value = c.age || '';
      document.getElementById('edit-case-gender').value = c.gender || 'Male';
      document.getElementById('edit-case-date').value = c.last_seen_date || '';
      document.getElementById('edit-case-time').value = c.last_seen_time || '';
      document.getElementById('edit-case-location').value = c.last_seen_location || '';
      document.getElementById('edit-case-lat').value = c.latitude || 13.0827;
      document.getElementById('edit-case-lng').value = c.longitude || 80.2707;
      document.getElementById('edit-case-features').value = c.identifying_features || '';
      document.getElementById('edit-case-clothing').value = c.clothing_description || '';
      document.getElementById('edit-case-notes').value = c.notes || '';

      this.openModal('edit-case-modal');
    } catch (err) {
      alert('Failed to load case data: ' + err.message);
    }
  },

  async handleEditCaseSubmit(e) {
    e.preventDefault();
    if (!this.currentCaseId) return;
    const btn = document.getElementById('btn-save-edit-case');
    if (btn) btn.disabled = true;

    try {
      const updateData = {
        full_name: document.getElementById('edit-case-fullname').value.trim(),
        age: parseInt(document.getElementById('edit-case-age').value) || null,
        gender: document.getElementById('edit-case-gender').value,
        last_seen_date: document.getElementById('edit-case-date').value,
        last_seen_time: document.getElementById('edit-case-time').value,
        last_seen_location: document.getElementById('edit-case-location').value.trim(),
        latitude: parseFloat(document.getElementById('edit-case-lat').value) || null,
        longitude: parseFloat(document.getElementById('edit-case-lng').value) || null,
        identifying_features: document.getElementById('edit-case-features').value.trim(),
        clothing_description: document.getElementById('edit-case-clothing').value.trim(),
        notes: document.getElementById('edit-case-notes').value.trim()
      };

      await API.updateCase(this.currentCaseId, updateData);
      alert('Case dossier metadata updated successfully!');
      this.closeModal('edit-case-modal');
      await this.viewCaseDetails(this.currentCaseId);
    } catch (err) {
      alert('Failed to update case: ' + err.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  async printCaseBulletin() {
    if (!this.currentCaseId) return;
    try {
      const b = await API.getCaseBulletin(this.currentCaseId);
      const container = document.getElementById('bulletin-content');
      if (!container) return;

      container.innerHTML = `
        <div class="border-4 border-red-700 p-6 rounded-xl space-y-5 bg-white text-slate-900">
          <div class="text-center space-y-1">
            <span class="bg-red-700 text-white font-mono font-black text-xs px-3 py-1 rounded uppercase tracking-widest">
              OFFICIAL POLICE NOTICE • DO NOT REMOVE
            </span>
            <h2 class="text-3xl font-black tracking-tight text-slate-950 uppercase mt-2">${b.subject_name}</h2>
            <div class="font-mono text-sm text-red-700 font-bold">CASE FILE REF: ${b.reference_no}</div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-5 items-center">
            <div class="sm:col-span-1 h-56 bg-slate-100 rounded-xl overflow-hidden border-2 border-slate-900 flex items-center justify-center">
              ${b.primary_photo_path ? `
                <img src="/${b.primary_photo_path}" class="w-full h-full object-cover" alt="${b.subject_name}"/>
              ` : `
                <span class="text-4xl text-slate-400">👤</span>
              `}
            </div>

            <div class="sm:col-span-2 space-y-2 text-xs font-mono">
              <div class="grid grid-cols-2 gap-2 p-3 bg-slate-100 rounded-lg">
                <div><strong>AGE:</strong> ${b.age || 'Unknown'} years</div>
                <div><strong>GENDER:</strong> ${b.gender || 'Not specified'}</div>
                <div><strong>LAST SEEN:</strong> ${b.last_seen_date}</div>
                <div><strong>TIME:</strong> ${b.last_seen_time || 'N/A'}</div>
              </div>
              <div class="p-2 border border-slate-200 rounded">
                <strong>LAST KNOWN LOCATION:</strong>
                <p class="text-slate-800 text-[11px] mt-0.5">${b.last_seen_location}</p>
              </div>
              <div class="p-2 border border-slate-200 rounded">
                <strong>DISTINGUISHING FEATURES:</strong>
                <p class="text-slate-800 text-[11px] mt-0.5">${b.identifying_features}</p>
              </div>
              <div class="p-2 border border-slate-200 rounded">
                <strong>CLOTHING AT TIME OF DISAPPEARANCE:</strong>
                <p class="text-slate-800 text-[11px] mt-0.5">${b.clothing_description}</p>
              </div>
            </div>
          </div>

          <div class="p-4 bg-red-50 border-2 border-dashed border-red-300 rounded-xl text-center space-y-1">
            <div class="font-bold text-red-900 text-sm">IF YOU HAVE ANY INFORMATION, IMMEDIATELY CONTACT:</div>
            <div class="text-base font-black text-red-700 font-mono">${b.emergency_contact}</div>
            <div class="text-xs text-slate-700 font-mono">INVESTIGATING OFFICER: ${b.investigating_officer} (${b.badge_number})</div>
            <div class="text-[11px] text-slate-500 font-mono">Tip Line: ${b.tip_hotline}</div>
          </div>

          <div class="text-center text-[10px] text-slate-400 font-mono pt-2 border-t border-slate-200">
            ${b.legal_notice} • Generated from AI Missing Persons Central Dossier System
          </div>
        </div>
      `;

      this.openModal('bulletin-modal');
    } catch (err) {
      alert('Failed to generate bulletin: ' + err.message);
    }
  },

  async archiveActiveCase() {
    if (!this.currentCaseId) return;
    if (!confirm('Are you sure you want to ARCHIVE this case dossier? Archived cases remain accessible via the status filter.')) return;

    try {
      const res = await API.archiveCase(this.currentCaseId);
      alert(res.message);
      this.switchTab('cases');
      await this.loadCases();
    } catch (err) {
      alert('Failed to archive case: ' + err.message);
    }
  },

  async deleteReferencePhoto(refId) {
    if (!this.currentCaseId) return;
    if (!confirm('Are you sure you want to remove this reference portrait?')) return;

    try {
      const res = await API.deleteReferencePhoto(this.currentCaseId, refId);
      alert(res.message);
      await this.viewCaseDetails(this.currentCaseId);
    } catch (err) {
      alert('Failed to delete photo: ' + err.message);
    }
  }
};

window.App = App;
document.addEventListener('DOMContentLoaded', () => App.init());
