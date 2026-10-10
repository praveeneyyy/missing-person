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
    } else {
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
    } catch (err) {
      alert('Failed to load case dossier: ' + err.message);
    }
  },

  // 3. Forensic Candidate Review Workbench (Module 6 Core)
  async loadReviewQueue() {
    try {
      const candidates = await API.getPendingCandidates();
      const container = document.getElementById('review-queue-list');
      if (!container) return;

      if (candidates.length === 0) {
        container.innerHTML = `
          <div class="p-16 text-center bg-white rounded-2xl border border-slate-200 shadow-sm space-y-3">
            <div class="w-16 h-16 mx-auto rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold text-2xl border border-emerald-200">
              ✓
            </div>
            <h3 class="text-lg font-extrabold text-slate-900">Review Queue Cleared</h3>
            <p class="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
              All potential candidate matches have been adjudicated with recorded rationale. New public sightings will appear here automatically.
            </p>
          </div>
        `;
        return;
      }

      container.innerHTML = candidates.map(c => {
        const scorePercent = (c.similarity_score * 100).toFixed(1);
        const isHigh = c.similarity_score >= 0.70;
        const tierLabel = isHigh ? 'HIGH CONFIDENCE (≥ 0.70)' : (c.similarity_score >= 0.50 ? 'MODERATE (0.50 - 0.69)' : 'LOW SIMILARITY');
        const tierBadgeClass = isHigh ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' : 'bg-amber-500/20 text-amber-300 border-amber-500/40';

        // Calculate geographical distance in km between Case last-seen and Sighting
        const distKm = MapManager.calculateDistanceKm(c.case_lat, c.case_lng, c.sighting_lat, c.sighting_lng);

        // Parse landmarks & bbox for canvases
        const sightingFaces = c.sighting_faces_json ? JSON.parse(c.sighting_faces_json) : [];
        const activeSightFace = sightingFaces[c.sighting_face_index] || sightingFaces[0] || {};
        const sightBbox = activeSightFace.bbox || null;
        const sightLandmarks = activeSightFace.landmarks || null;

        const refBbox = c.ref_bbox_json ? JSON.parse(c.ref_bbox_json) : null;
        const refLandmarks = c.ref_landmarks_json ? JSON.parse(c.ref_landmarks_json) : null;

        return `
          <div class="bg-white rounded-2xl border border-slate-200 shadow-md overflow-hidden mb-8">
            <!-- Command Console Header -->
            <div class="bg-slate-950 text-white p-5 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4">
              <div class="flex items-center gap-3">
                <span class="pulse-indicator pulse-amber"></span>
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-mono font-extrabold text-cyan-400 text-sm tracking-wide">LEAD ADJUDICATION #${c.candidate_id}</span>
                    <span class="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono border border-slate-700">Rank #${c.rank}</span>
                  </div>
                  <div class="text-xs text-slate-400 mt-0.5">
                    Sighting <strong class="text-slate-200 font-mono">${c.receipt_no}</strong> correlated against Case <strong class="text-slate-200 font-mono">${c.reference_no}</strong> (${c.person_name})
                  </div>
                </div>
              </div>

              <!-- Biometric Match Score Badge -->
              <div class="flex items-center gap-4">
                <div class="text-right">
                  <div class="font-mono text-2xl font-black ${isHigh ? 'text-emerald-400' : 'text-amber-400'}">
                    ${scorePercent}%
                  </div>
                  <div class="text-[10px] font-mono uppercase tracking-wider text-slate-400">${tierLabel}</div>
                </div>

                <div class="h-10 w-px bg-slate-800"></div>

                <span class="badge-tactical badge-under_review">
                  Pending Human Review
                </span>
              </div>
            </div>

            <!-- Mandatory Ethical & Legal Caution Banner -->
            <div class="bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent border-b border-amber-500/20 px-6 py-2.5 text-xs text-amber-900 flex items-center gap-2.5">
              <span class="text-base">⚖️</span>
              <div>
                <span class="font-bold">MANDATORY INVESTIGATION GOVERNANCE:</span>
                <span>Biometric similarity scores are mathematical ranking signals only. Autonomous identification is prohibited. Review officers must record affirmative written findings.</span>
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
            <div class="bg-slate-50 border-t border-b border-slate-200 px-6 py-3 flex flex-wrap items-center justify-between gap-4 text-xs">
              <div class="flex items-center gap-6 font-mono">
                <div>
                  <span class="text-slate-400 text-[10px] block">SPATIAL SEPARATION</span>
                  <span class="font-bold text-slate-800">${distKm ? `${distKm} km from origin` : 'Coordinates pending'}</span>
                </div>
                <div>
                  <span class="text-slate-400 text-[10px] block">AI FEATURE VECTOR</span>
                  <span class="font-bold text-slate-800">${c.model_version} (128-D)</span>
                </div>
                <div>
                  <span class="text-slate-400 text-[10px] block">METRIC DISTANCE</span>
                  <span class="font-bold text-slate-800">Cosine: ${c.similarity_score.toFixed(4)}</span>
                </div>
              </div>

              <div class="text-slate-500 text-[11px]">
                Click an adjudication action below to open the formal decision dialog.
              </div>
            </div>

            <!-- Adjudication Action Command Bar -->
            <div class="p-6 bg-white flex flex-wrap items-center justify-between gap-4">
              <div class="flex items-center gap-2">
                <span class="text-xs text-slate-500 font-semibold">Quick Decision:</span>
                <button onclick="App.openReviewModal(${c.candidate_id}, 'rejected')" class="px-3.5 py-2 text-xs font-bold rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 transition">
                  Reject Lead
                </button>
                <button onclick="App.openReviewModal(${c.candidate_id}, 'request_more_info')" class="px-3.5 py-2 text-xs font-bold rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 transition">
                  Request Witness Info
                </button>
                <button onclick="App.openReviewModal(${c.candidate_id}, 'escalated')" class="px-3.5 py-2 text-xs font-bold rounded-xl bg-orange-50 hover:bg-orange-100 text-orange-800 border border-orange-200 transition">
                  Escalate to Field Team
                </button>
              </div>

              <button onclick="App.openReviewModal(${c.candidate_id}, 'verified')" class="px-5 py-2.5 text-xs font-extrabold rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white shadow-md transition flex items-center gap-1.5">
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
    } catch (err) {
      alert('Review submission failed: ' + err.message);
    }
  },

  // 4. Public Sighting Submission
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

      // Populate receipt modal
      document.getElementById('receipt-number-display').innerText = res.receipt_no;
      document.getElementById('receipt-faces-count').innerText = `${res.faces_detected_count} face(s) processed by AI`;
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

    try {
      const res = await API.lookupReceipt(receiptNo);
      const container = document.getElementById('lookup-result-box');
      container.classList.remove('hidden');
      container.innerHTML = `
        <div class="p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <span class="text-[10px] font-mono uppercase text-slate-400 block">RECEIPT REFERENCE</span>
              <span class="font-mono font-extrabold text-blue-700 text-base">${res.receipt_no}</span>
            </div>
            <span class="badge-tactical badge-under_review">${res.status}</span>
          </div>
          <div class="space-y-1.5 text-xs text-slate-600 font-mono">
            <div><strong>Location:</strong> ${res.location_name}</div>
            <div><strong>Sighting Date:</strong> ${res.sighting_date} ${res.sighting_time || ''}</div>
            <div><strong>Submitted:</strong> ${res.submitted_at}</div>
          </div>
          <div class="p-3 bg-blue-50/60 rounded-xl border border-blue-100 text-[11px] text-blue-900 leading-relaxed">
            ℹ️ <strong>Status Notice:</strong> ${res.notice}
          </div>
        </div>
      `;
    } catch (err) {
      alert(err.message);
    }
  },

  // 7. Audit Logs View
  async loadAuditLogs() {
    try {
      const logs = await API.getAuditLogs();
      const tbody = document.getElementById('audit-table-body');
      if (!tbody) return;

      tbody.innerHTML = logs.map(l => `
        <tr class="border-b border-slate-100 hover:bg-slate-50 font-mono text-xs transition">
          <td class="py-3 px-4 text-slate-500 whitespace-nowrap">${l.created_at}</td>
          <td class="py-3 px-4 font-bold text-slate-900">${l.actor_name}</td>
          <td class="py-3 px-4">
            <span class="text-blue-700 font-bold bg-blue-50 px-2 py-0.5 rounded border border-blue-200">${l.action}</span>
          </td>
          <td class="py-3 px-4 text-slate-600">${l.resource_type} #${l.resource_id}</td>
          <td class="py-3 px-4 text-slate-500 truncate max-w-sm">${JSON.stringify(l.details)}</td>
        </tr>
      `).join('');
    } catch (err) {
      console.error('Error loading audit logs:', err);
    }
  },

  // 8. AI Quality & Benchmark View with Interactive Threshold Simulator
  async loadBenchmark() {
    try {
      const b = await API.getBenchmark();
      const container = document.getElementById('benchmark-metrics-box');
      if (!container) return;

      container.innerHTML = `
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div class="text-xs text-slate-400 font-mono uppercase tracking-wider">Recall@1 Accuracy</div>
            <div class="text-3xl font-black text-emerald-600 mt-2 font-mono">${b.metrics.recall_at_1_percent}%</div>
            <div class="text-xs text-slate-500 mt-1">Exact Top-1 enrolled self-match</div>
          </div>
          <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div class="text-xs text-slate-400 font-mono uppercase tracking-wider">Recall@5 Accuracy</div>
            <div class="text-3xl font-black text-blue-600 mt-2 font-mono">${b.metrics.recall_at_5_percent}%</div>
            <div class="text-xs text-slate-500 mt-1">Target in Top-5 candidate retrieval</div>
          </div>
          <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div class="text-xs text-slate-400 font-mono uppercase tracking-wider">False Match Rate (≥ 0.70)</div>
            <div class="text-3xl font-black text-slate-900 mt-2 font-mono">${b.metrics.false_match_rate_high_threshold_percent}%</div>
            <div class="text-xs text-slate-500 mt-1">Disjoint pairs false-positive risk</div>
          </div>
          <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div class="text-xs text-slate-400 font-mono uppercase tracking-wider">Vector Search Latency</div>
            <div class="text-3xl font-black text-cyan-600 mt-2 font-mono">${b.latency_profile.all_pairs_search_time_ms} ms</div>
            <div class="text-xs text-slate-500 mt-1">All-pairs pairwise cosine search</div>
          </div>
        </div>

        <!-- Interactive Operating Threshold Calibration Simulator -->
        <div class="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
          <div class="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h3 class="text-lg font-bold text-slate-900">Interactive Cosine Threshold Calibration Simulator</h3>
              <p class="text-xs text-slate-500 mt-0.5">Test operating point trade-offs between investigative sensitivity and false-alarm burden.</p>
            </div>
            <div class="text-right">
              <span class="font-mono text-xl font-black text-blue-700" id="sim-thresh-val">${this.simulatedThreshold.toFixed(2)}</span>
              <span class="text-[10px] text-slate-400 block font-mono">SELECTED OPERATING POINT</span>
            </div>
          </div>

          <!-- Slider -->
          <div class="space-y-2">
            <div class="flex justify-between text-xs font-mono text-slate-500">
              <span>0.40 (High Recall / Broad Leads)</span>
              <span>0.70 (Calibrated High Confidence)</span>
              <span>0.90 (Strict / Near-Identical)</span>
            </div>
            <input type="range" id="sim-thresh-slider" min="0.40" max="0.90" step="0.05" value="${this.simulatedThreshold}" oninput="App.updateThresholdSimulation(this.value)" class="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600">
          </div>

          <div id="sim-analysis-box" class="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 space-y-1">
            <!-- Updated via JS -->
          </div>
        </div>
      `;

      this.updateThresholdSimulation(this.simulatedThreshold);
    } catch (err) {
      console.error('Error loading benchmark:', err);
    }
  },

  updateThresholdSimulation(val) {
    this.simulatedThreshold = parseFloat(val);
    const valDisplay = document.getElementById('sim-thresh-val');
    if (valDisplay) valDisplay.innerText = this.simulatedThreshold.toFixed(2);

    const box = document.getElementById('sim-analysis-box');
    if (!box) return;

    let tierDesc = '';
    if (this.simulatedThreshold >= 0.75) {
      tierDesc = `<strong>Ultra-High Precision Operating Point:</strong> Minimal to 0% false matches on diverse test sets. Suitable for automatic priority alerts and immediate patrol dispatch.`;
    } else if (this.simulatedThreshold >= 0.65) {
      tierDesc = `<strong>Recommended Calibrated Operating Point (0.70):</strong> Optimal balance. Catches real sightings with slight facial angle/lighting variation while maintaining low false-alarm risk.`;
    } else {
      tierDesc = `<strong>High-Sensitivity / Broad Discovery Mode:</strong> Flags candidate matches with lower similarity (0.50 - 0.64). Increases reviewer workload but reduces risk of missed leads.`;
    }

    box.innerHTML = `
      <div class="font-mono font-bold text-slate-900">Analysis for Cosine Threshold $\\ge$ ${this.simulatedThreshold.toFixed(2)}:</div>
      <div class="leading-relaxed text-slate-600 mt-1">${tierDesc}</div>
    `;
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
