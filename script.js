
/* =========================================================
   TODO DERECHO VECINO
   Semana 8 - Frontend
   Conexión con API Gateway
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {
  // -------------------------------------------------------
  // 1. Configuración y referencias al HTML
  // -------------------------------------------------------

  const API_URL = window.TDV_CONFIG?.API_URL;

  const menuButton = document.getElementById("menuButton");
  const mainMenu = document.getElementById("mainMenu");

  const welcomeScreen = document.getElementById("inicio");
  const consultationScreen = document.getElementById("consultationScreen");

  const startButton = document.getElementById("startConsultation");
  const chatMessages = document.getElementById("chatMessages");
  const consultationForm = document.getElementById("consultationForm");
  const questionInput = document.getElementById("questionInput");
  const sendButton = document.getElementById("sendQuestion");

  const REQUEST_TIMEOUT = 35000;

  // -------------------------------------------------------
  // 2. Validación de elementos necesarios
  // -------------------------------------------------------

  const requiredElements = [
    welcomeScreen,
    consultationScreen,
    startButton,
    chatMessages,
    consultationForm,
    questionInput,
    sendButton
  ];

  if (requiredElements.some(element => !element)) {
    console.error(
      "Todo Derecho Vecino: faltan elementos HTML necesarios para iniciar."
    );
    return;
  }

  // -------------------------------------------------------
  // 3. Funciones auxiliares
  // -------------------------------------------------------

  function createElement(tag, className, text = "") {
    const element = document.createElement(tag);

    if (className) {
      element.className = className;
    }

    if (text !== undefined && text !== null) {
      element.textContent = String(text);
    }

    return element;
  }

  function scrollChatToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function addMessage(text, type = "assistant") {
    const message = createElement("div", `message message-${type}`);
    const paragraph = createElement("p", "", text);

    message.appendChild(paragraph);
    chatMessages.appendChild(message);

    scrollChatToBottom();

    return message;
  }

  function normalizeArray(value) {
    if (Array.isArray(value)) {
      return value;
    }

    if (typeof value === "string" && value.trim()) {
      return [value];
    }

    return [];
  }

   // -------------------------------------------------------
  // 4. Navegación entre pantallas
  // -------------------------------------------------------

  const aboutScreen = document.getElementById("acerca");
  const homeLink = mainMenu?.querySelector('a[href="#inicio"]');
  const aboutLink = mainMenu?.querySelector('a[href="#acerca"]');

  function closeMenu() {
    if (mainMenu && menuButton) {
      mainMenu.hidden = true;
      menuButton.setAttribute("aria-expanded", "false");
    }
  }

  function showScreen(screen) {
    welcomeScreen.hidden = screen !== "home";
    consultationScreen.hidden = screen !== "consultation";

    if (aboutScreen) {
      aboutScreen.hidden = screen !== "about";
    }

    closeMenu();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function openHome() {
    showScreen("home");
  }

  function openAbout() {
    showScreen("about");
  }

  function openConsultation() {
    showScreen("consultation");

    questionInput.focus();

    if (chatMessages.children.length === 0) {
      addMessage(
        "Hola. Soy el asistente de Todo Derecho Vecino. " +
        "Puedes escribir tu consulta sobre uso de suelo y normatividad en la CDMX.",
        "assistant"
      );
    }
  }

  startButton.addEventListener("click", openConsultation);

  if (homeLink) {
    homeLink.addEventListener("click", event => {
      event.preventDefault();
      openHome();
    });
  }

  if (aboutLink) {
    aboutLink.addEventListener("click", event => {
      event.preventDefault();
      openAbout();
    });
  }

  // -------------------------------------------------------
  // 5. Menú principal
  // -------------------------------------------------------

  if (menuButton && mainMenu) {
    menuButton.addEventListener("click", () => {
      const isExpanded =
        menuButton.getAttribute("aria-expanded") === "true";

      menuButton.setAttribute("aria-expanded", String(!isExpanded));
      mainMenu.hidden = isExpanded;
    });
  }

  // -------------------------------------------------------
  // 6. Indicador de carga
  // -------------------------------------------------------

  function showLoading() {
    const loading = createElement(
      "div",
      "message message-system loading-indicator",
      "Analizando tu consulta. Esto puede tomar unos segundos..."
    );

    loading.setAttribute("role", "status");
    loading.setAttribute("aria-live", "polite");

    chatMessages.appendChild(loading);
    scrollChatToBottom();

    return loading;
  }

  // -------------------------------------------------------
  // 7. Presentación de citas jurídicas
  // -------------------------------------------------------

  function renderCitations(citations, parent) {
    if (!Array.isArray(citations) || citations.length === 0) {
      return;
    }

    const section = createElement("section", "citations");
    const heading = createElement("h3", "", "Fundamentos y referencias");

    section.appendChild(heading);

    citations.forEach((citation, index) => {
      if (!citation || typeof citation !== "object") {
        return;
      }

      const citationBox = createElement("article", "citation");

      const referenceId =
        citation.id || `F${index + 1}`;

      const title = createElement(
        "h3",
        "",
        `[${referenceId}] ${citation.documento || "Documento jurídico"}`
      );

      citationBox.appendChild(title);

      if (citation.articulo) {
        citationBox.appendChild(
          createElement("p", "citation-reference",
            `Artículo o sección: ${citation.articulo}`)
        );
      }

      if (citation.cita_legal) {
        citationBox.appendChild(
          createElement("p", "", citation.cita_legal)
        );
      }

      if (citation.segmento) {
        citationBox.appendChild(
          createElement("p", "", `Segmento: ${citation.segmento}`)
        );
      }

      if (citation.fragmento) {
        const fragment = createElement(
          "p",
          "citation-fragment",
          `Fragmento recuperado: ${citation.fragmento}`
        );

        citationBox.appendChild(fragment);
      }

      if (citation.pendiente_revision === true) {
        const warning = createElement(
          "p",
          "review-warning",
          "Esta referencia está pendiente de revisión jurídica. " +
          "No debe considerarse un fundamento legal verificado."
        );

        warning.setAttribute("role", "note");
        citationBox.appendChild(warning);
      }

      section.appendChild(citationBox);
    });

    if (section.children.length > 1) {
      parent.appendChild(section);
    }
  }

  // -------------------------------------------------------
  // 8. Presentación de limitaciones
  // -------------------------------------------------------

  function renderLimitations(limitations, parent) {
    const items = normalizeArray(limitations);

    if (items.length === 0) {
      return;
    }

    const section = createElement("section", "limitations");
    const heading = createElement("h3", "", "Limitaciones de esta respuesta");

    section.appendChild(heading);

    const list = createElement("ul", "limitations-list");

    items.forEach(item => {
      const text =
        typeof item === "string"
          ? item
          : JSON.stringify(item);

      list.appendChild(createElement("li", "", text));
    });

    section.appendChild(list);
    parent.appendChild(section);
  }

  // -------------------------------------------------------
  // 9. Presentación de la respuesta de la API
  // -------------------------------------------------------

  function renderApiResponse(data) {
    const responseMessage = createElement(
      "div",
      "message message-assistant"
    );

    const answer = typeof data.answer === "string"
      ? data.answer.trim()
      : "";

    if (answer) {
      const answerParagraph = createElement("p", "", answer);
      responseMessage.appendChild(answerParagraph);
    } else {
      responseMessage.appendChild(
        createElement(
          "p",
          "",
          "La API no proporcionó un texto de respuesta. " +
          "Consulta las limitaciones o intenta nuevamente."
        )
      );
    }

    renderCitations(data.citations, responseMessage);
    renderLimitations(data.limitations, responseMessage);

    if (data.status && data.status !== "answered") {
      const statusNote = createElement(
        "p",
        "review-warning",
        `Estado informado por el sistema: ${data.status}.`
      );

      responseMessage.appendChild(statusNote);
    }

    if (data.model_id) {
      const modelInfo = createElement(
        "p",
        "response-model",
        `Modelo: ${data.model_id}`
      );

      responseMessage.appendChild(modelInfo);
    }

    chatMessages.appendChild(responseMessage);
    scrollChatToBottom();
  }

  // -------------------------------------------------------
  // 10. Manejo de errores
  // -------------------------------------------------------

  function showApiError(message) {
    const errorMessage = addMessage(message, "error");
    errorMessage.setAttribute("role", "alert");
  }

  // -------------------------------------------------------
  // 11. Envío de consultas a la API
  // -------------------------------------------------------

  async function sendQuestion(question) {
    if (!API_URL) {
      showApiError(
        "No se encontró la dirección de la API. " +
        "Verifica el archivo config.js."
      );
      return;
    }

    const loading = showLoading();
    const controller = new AbortController();

    const timeoutId = setTimeout(
      () => controller.abort(),
      REQUEST_TIMEOUT
    );

    sendButton.disabled = true;
    questionInput.disabled = true;

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question: question
        }),
        signal: controller.signal
      });

      const responseText = await response.text();

      let data;

      try {
        data = responseText ? JSON.parse(responseText) : {};
      } catch {
        throw new Error(
          "El servidor respondió con un formato que no es JSON válido."
        );
      }

      if (!response.ok) {
        const detail =
          data.message ||
          data.error ||
          data.detail ||
          `Error HTTP ${response.status}`;

        throw new Error(detail);
      }

      if (!data || typeof data !== "object" || Array.isArray(data)) {
        throw new Error("La API devolvió una respuesta inesperada.");
      }

      renderApiResponse(data);

      questionInput.value = "";

    } catch (error) {
      console.error("Error al consultar la API:", error);

      if (error.name === "AbortError") {
        showApiError(
          "La consulta excedió el tiempo de espera. " +
          "Puedes intentar nuevamente."
        );
      } else if (error instanceof TypeError) {
        showApiError(
          "No fue posible establecer conexión con el servidor. " +
          "Verifica tu conexión e intenta nuevamente."
        );
      } else {
        showApiError(
          `No fue posible procesar la consulta: ${error.message}`
        );
      }

    } finally {
      clearTimeout(timeoutId);
      loading.remove();

      sendButton.disabled = false;
      questionInput.disabled = false;
      questionInput.focus();

      scrollChatToBottom();
    }
  }

  // -------------------------------------------------------
  // 12. Evento de envío del formulario
  // -------------------------------------------------------

  consultationForm.addEventListener("submit", async event => {
    event.preventDefault();

    const question = questionInput.value.trim();

    if (!question) {
      questionInput.focus();
      return;
    }

    if (sendButton.disabled) {
      return;
    }

    addMessage(question, "user");

    await sendQuestion(question);
  });

});
