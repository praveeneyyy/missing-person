// Advanced GIS & Investigation Map Manager using Leaflet.js
const MapManager = {
  mainMap: null,
  pickerMap: null,
  pickerMarker: null,
  activeLeadLine: null,

  initMainMap(containerId = 'investigation-map') {
    const el = document.getElementById(containerId);
    if (!el) return;

    if (this.mainMap) {
      this.mainMap.remove();
      this.mainMap = null;
    }

    // Default center: Chennai, Tamil Nadu
    this.mainMap = L.map(containerId, {
      zoomControl: true,
      attributionControl: true
    }).setView([13.05, 80.22], 11);

    // Clean modern OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 18
    }).addTo(this.mainMap);

    this.loadMapPoints();
  },

  calculateDistanceKm(lat1, lon1, lat2, lon2) {
    if (!lat1 || !lon1 || !lat2 || !lon2) return null;
    const R = 6371; // Earth radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return (R * c).toFixed(1);
  },

  async loadMapPoints() {
    if (!this.mainMap) return;

    try {
      const data = await API.getMapPoints();
      const bounds = [];

      // High-precision custom SVG icon generator
      const createTacticalPin = (color, label, sub) => L.divIcon({
        className: 'tactical-map-pin',
        html: `
          <div style="display: flex; flex-direction: column; align-items: center; cursor: pointer;">
            <div style="background: ${color}; color: white; padding: 4px 8px; border-radius: 6px; font-weight: 800; font-family: monospace; font-size: 11px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); border: 1.5px solid white; display: flex; align-items: center; gap: 4px;">
              <span>${label}</span>
              ${sub ? `<span style="font-size: 9px; opacity: 0.85;">${sub}</span>` : ''}
            </div>
            <div style="width: 0; height: 0; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid ${color};"></div>
          </div>
        `,
        iconSize: [60, 36],
        iconAnchor: [30, 36]
      });

      // 1. Plot Enrolled Missing-Person Cases
      data.cases.forEach(c => {
        if (c.latitude && c.longitude) {
          bounds.push([c.latitude, c.longitude]);

          const marker = L.marker([c.latitude, c.longitude], {
            icon: createTacticalPin('#2563EB', c.reference_no, 'ORIGIN')
          }).addTo(this.mainMap);

          const photoHtml = c.photo_path
            ? `<img src="/${c.photo_path}" style="width: 100%; height: 110px; object-fit: cover; border-radius: 6px; margin-bottom: 8px;" alt="${c.full_name}"/>`
            : '';

          marker.bindPopup(`
            <div style="font-family: -apple-system, sans-serif; font-size: 12px; max-width: 240px; padding: 2px;">
              ${photoHtml}
              <div style="font-family: monospace; font-weight: 800; color: #2563EB; font-size: 13px;">${c.reference_no}</div>
              <div style="font-weight: 700; font-size: 15px; color: #0F172A; margin-top: 2px;">${c.full_name}</div>
              <div style="color: #64748B; font-size: 11px; margin-top: 4px;"><strong>Last Seen:</strong> ${c.last_seen_date}</div>
              <div style="color: #475569; font-size: 11px; margin-top: 2px;"><strong>Location:</strong> ${c.last_seen_location}</div>
              <div style="margin-top: 8px; display: flex; align-items: center; justify-content: space-between;">
                <span class="badge-tactical badge-${c.status}">${c.status}</span>
                <button onclick="App.viewCaseDetails(${c.id})" style="background: #2563EB; color: white; border: none; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; cursor: pointer;">Open Dossier</button>
              </div>
            </div>
          `);
        }
      });

      // 2. Plot Sighting Reports
      data.sightings.forEach(s => {
        if (s.latitude && s.longitude) {
          bounds.push([s.latitude, s.longitude]);

          const isVerified = s.status === 'verified_match';
          const isHighSim = s.max_similarity >= 0.70;
          const pinColor = isVerified ? '#10B981' : (isHighSim ? '#F59E0B' : '#64748B');
          const simPct = s.max_similarity ? `${Math.round(s.max_similarity * 100)}%` : null;

          const marker = L.marker([s.latitude, s.longitude], {
            icon: createTacticalPin(pinColor, s.receipt_no, simPct)
          }).addTo(this.mainMap);

          // Add accuracy circle around sighting
          L.circle([s.latitude, s.longitude], {
            color: pinColor,
            fillColor: pinColor,
            fillOpacity: 0.12,
            radius: 800 // 800 meter approximate radius
          }).addTo(this.mainMap);

          const simBadge = s.max_similarity 
            ? `<div style="background: ${isHighSim ? '#ECFDF5' : '#FFFBEB'}; color: ${isHighSim ? '#065F46' : '#92400E'}; padding: 4px 8px; border-radius: 4px; font-weight: 700; font-size: 11px; margin-top: 6px; font-family: monospace;">
                AI Correlation: ${(s.max_similarity * 100).toFixed(1)}% Match
               </div>`
            : '';

          marker.bindPopup(`
            <div style="font-family: -apple-system, sans-serif; font-size: 12px; max-width: 240px; padding: 2px;">
              <div style="font-family: monospace; font-weight: 800; color: #D97706; font-size: 13px;">${s.receipt_no}</div>
              <div style="font-weight: 700; font-size: 14px; color: #0F172A; margin-top: 2px;">Reported Sighting</div>
              <div style="color: #64748B; font-size: 11px; margin-top: 4px;"><strong>Date:</strong> ${s.sighting_date}</div>
              <div style="color: #475569; font-size: 11px; margin-top: 2px;"><strong>Site:</strong> ${s.location_name}</div>
              ${simBadge}
              <div style="margin-top: 8px; display: flex; align-items: center; justify-content: space-between;">
                <span class="badge-tactical badge-${s.status}">${s.status}</span>
                <button onclick="App.switchTab('review-queue')" style="background: #0F172A; color: white; border: none; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; cursor: pointer;">Review Queue</button>
              </div>
            </div>
          `);
        }
      });

      if (bounds.length > 0) {
        this.mainMap.fitBounds(bounds, { padding: [50, 50] });
      }
    } catch (err) {
      console.error('Failed to load map points:', err);
    }
  },

  // Interactive Location Picker for Sighting Submissions & Case Enrollment
  initLocationPicker(containerId, latInputId, lngInputId, locationNameId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    if (this.pickerMap) {
      this.pickerMap.remove();
      this.pickerMap = null;
    }

    const defaultLat = 13.0827;
    const defaultLng = 80.2707;

    this.pickerMap = L.map(containerId).setView([defaultLat, defaultLng], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap'
    }).addTo(this.pickerMap);

    this.pickerMarker = L.marker([defaultLat, defaultLng], { draggable: true }).addTo(this.pickerMap);

    const updateInputs = (lat, lng) => {
      const latEl = document.getElementById(latInputId);
      const lngEl = document.getElementById(lngInputId);
      if (latEl) latEl.value = lat.toFixed(5);
      if (lngEl) lngEl.value = lng.toFixed(5);
    };

    updateInputs(defaultLat, defaultLng);

    this.pickerMap.on('click', (e) => {
      this.pickerMarker.setLatLng(e.latlng);
      updateInputs(e.latlng.lat, e.latlng.lng);
    });

    this.pickerMarker.on('dragend', (e) => {
      const pos = e.target.getLatLng();
      updateInputs(pos.lat, pos.lng);
    });
  }
};
