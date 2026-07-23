(() => {
  const moduleDetails = {
    Population: {
      summary: "Who is present, where, and how vulnerability changes by hour.",
      functions: [
        "Time-dependent occupancy",
        "Sensitive facilities and groups",
        "Potential exposure by route",
        "Protection-priority ranking",
      ],
    },
    Dispatch: {
      summary: "Which resources can respond and which access remains defensible.",
      functions: [
        "Resource availability",
        "Mobilisation and travel time",
        "Access conflicts",
        "Human approval before dispatch",
      ],
    },
    Traffic: {
      summary: "How congestion, closures and road incidents alter reliability.",
      functions: [
        "Congestion and wet-road penalties",
        "Blocked street segments",
        "Fastest versus low-conflict route",
        "Continuous recalculation",
      ],
    },
    Environment: {
      summary: "How weather, water and sensitive areas change the response.",
      functions: [
        "Wind-informed plume",
        "Rainfall and runoff assumptions",
        "Water and ecological receptors",
        "Containment priorities",
      ],
    },
  };

  const activeByStep = [
    ["Traffic", "Environment"],
    ["Population"],
    ["Population", "Dispatch", "Traffic", "Environment"],
    ["Population", "Dispatch", "Traffic"],
    ["Dispatch", "Traffic", "Environment"],
    ["Population", "Dispatch", "Traffic", "Environment"],
  ];

  function replaceButtonLabel(selector, label) {
    const button = document.querySelector(selector);
    if (!button || button.dataset.skyrouteLabel === label) return;
    const textNode = [...button.childNodes].find((node) => node.nodeType === Node.TEXT_NODE);
    if (textNode) textNode.textContent = ` ${label}`;
    else button.append(document.createTextNode(` ${label}`));
    button.dataset.skyrouteLabel = label;
  }

  function currentPitchStep(controller) {
    const progress = controller.querySelector(".pitch-progress");
    if (!progress) return 0;
    const buttons = [...progress.querySelectorAll("button")];
    const activeIndex = buttons.findIndex((button) => button.classList.contains("active"));
    return activeIndex < 0 ? 0 : activeIndex;
  }

  function addPitchModules() {
    const controller = document.querySelector(".pitch-controller");
    if (!controller) return;
    const step = currentPitchStep(controller);
    const existing = controller.querySelector(".pitch-module-tools");
    if (existing?.dataset.step === String(step)) return;
    existing?.remove();

    const strip = document.createElement("div");
    strip.className = "pitch-module-tools";
    strip.dataset.step = String(step);
    const active = new Set(activeByStep[step] || []);

    Object.entries(moduleDetails).forEach(([name, detail]) => {
      const item = document.createElement("details");
      if (active.has(name)) item.classList.add("is-active");
      const functions = detail.functions.map((text) => `<li>${text}</li>`).join("");
      item.innerHTML = `
        <summary>${active.has(name) ? "●" : "○"} ${name}</summary>
        <div class="module-popover">
          <strong>${active.has(name) ? "Activated in this scene" : "Available to the agent"}</strong>
          <p>${detail.summary}</p>
          <ul>${functions}</ul>
        </div>`;
      strip.append(item);
    });

    const progress = controller.querySelector(".pitch-progress");
    progress?.insertAdjacentElement("afterend", strip);
  }

  function addMapUtilities() {
    document.querySelectorAll(".map-stage").forEach((stage) => {
      if (!stage.querySelector(".map-north-indicator")) {
        const north = document.createElement("div");
        north.className = "map-north-indicator";
        north.setAttribute("aria-label", "North");
        north.innerHTML = "<span>N<br>↑</span>";
        stage.append(north);
      }
    });
  }

  function enhance() {
    replaceButtonLabel(".topbar-actions .quiet-button", "Data");
    replaceButtonLabel(".topbar-actions .present-button", "Presentation");
    addPitchModules();
    addMapUtilities();
  }

  const observer = new MutationObserver(enhance);
  observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true });
  window.addEventListener("DOMContentLoaded", enhance);
  enhance();
})();
