// ==UserScript==
// @name         SportsCardsPro - Add Card Form Helpers
// @namespace    http://tampermonkey.net/
// @version      1.4
// @author       jessedp <jessedp@gmail.com>
// @description  Save and auto-populate cost basis and purchase date for sports cards form, collapse grading
// @match        https://www.sportscardspro.com/publish-offer*
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  console.log("Sports Cards Pro Form Helper Script Started");

  // Keys for localStorage
  const COST_BASIS_KEY = "sportscards_cost_basis";
  const DATE_PURCHASED_KEY = "sportscards_date_purchased";
  const TIMESTAMP_KEY = "sportscards_timestamp";

  // Safer element selector with logging
  function safeQuerySelector(selector) {
    const element = document.querySelector(selector);
    if (!element) {
      console.warn(`Could not find element with selector: ${selector}`);
    }
    return element;
  }

  // Function to save form values to localStorage
  function saveFormValues(event) {
    console.log("Attempting to save form values");

    const costBasisInput = safeQuerySelector('input[name="cost-basis"]');
    const datePurchasedInput = safeQuerySelector(
      'input[name="date-purchased"]'
    );
    const submitButton = safeQuerySelector(
      'input[type="submit"][value="Add Item"][class="medium button blue"]'
    );

    if (costBasisInput && datePurchasedInput && submitButton) {
      try {
        localStorage.setItem(COST_BASIS_KEY, costBasisInput.value);
        localStorage.setItem(DATE_PURCHASED_KEY, datePurchasedInput.value);
        localStorage.setItem(TIMESTAMP_KEY, Date.now().toString());
        console.log("Form values saved to localStorage");
      } catch (error) {
        console.error("Error saving to localStorage:", error);
      }
    } else {
      console.error("Could not find one or more required elements");
      console.log("costBasisInput:", costBasisInput);
      console.log("datePurchasedInput:", datePurchasedInput);
      console.log("submitButton:", submitButton);
    }
  }

  // Function to clear stored values
  function clearStoredValues() {
    const costBasisInput = safeQuerySelector('input[name="cost-basis"]');
    const datePurchasedInput = safeQuerySelector(
      'input[name="date-purchased"]'
    );

    if (costBasisInput && datePurchasedInput) {
      costBasisInput.value = "";
      datePurchasedInput.value = "";

      localStorage.removeItem(COST_BASIS_KEY);
      localStorage.removeItem(DATE_PURCHASED_KEY);
      localStorage.removeItem(TIMESTAMP_KEY);

      console.log("Stored values cleared");
    }
  }

  // Function to populate form with stored values
  function populateFormFromStorage() {
    const costBasisInput = safeQuerySelector('input[name="cost-basis"]');
    const datePurchasedInput = safeQuerySelector(
      'input[name="date-purchased"]'
    );

    if (costBasisInput && datePurchasedInput) {
      const storedTimestamp = localStorage.getItem(TIMESTAMP_KEY);

      if (storedTimestamp) {
        const currentTime = Date.now();
        const oneHourAgo = currentTime - 60 * 60 * 1000;

        if (parseInt(storedTimestamp) > oneHourAgo) {
          const storedCostBasis = localStorage.getItem(COST_BASIS_KEY);
          const storedDatePurchased = localStorage.getItem(DATE_PURCHASED_KEY);

          if (storedCostBasis) costBasisInput.value = storedCostBasis;
          if (storedDatePurchased)
            datePurchasedInput.value = storedDatePurchased;

          console.log("Form populated from localStorage");
        }
      }
    }
  }

  // Function to add clear button
  function addClearButton() {
    const costBasisInput = safeQuerySelector('input[name="cost-basis"]');

    if (costBasisInput) {
      const clearButton = document.createElement("button");
      clearButton.textContent = "✖";
      clearButton.style.marginLeft = "5px";
      clearButton.style.cursor = "pointer";
      clearButton.type = "button";
      clearButton.addEventListener("click", clearStoredValues);

      costBasisInput.parentNode.insertBefore(
        clearButton,
        costBasisInput.nextSibling
      );
      console.log("Clear button added");
    }
  }

  // Function to create and manage grading info div
  function createGradingInfoDiv() {
    // Find the target divs
    const includesDiv = safeQuerySelector("#includes");
    const gradecoDiv = safeQuerySelector("#gradeco");
    const certidDiv = safeQuerySelector("#certid");

    if (includesDiv && gradecoDiv && certidDiv) {
      // Create main container
      const gradingInfoContainer = document.createElement("div");
      gradingInfoContainer.style.border = "1px solid #ccc";
      gradingInfoContainer.style.marginBottom = "5px";
      gradingInfoContainer.style.position = "relative";
      // gradingInfoContainer.style.width = 'fit-content';
      // #gradeco > h3 > span

      const lSpan = document.querySelector("#includes > label > select");
      const qDiv = document.querySelector("#gradeco > h3 > div.question_mark");

      const computedWidth =
        100 +
        parseInt(
          window
            .getComputedStyle(lSpan)
            .getPropertyValue("width")
            .replace("px", "")
        ) +
        parseInt(
          window
            .getComputedStyle(qDiv)
            .getPropertyValue("width")
            .replace("px", "")
        );
      console.log("computedWidth", computedWidth);

      gradingInfoContainer.style.width = computedWidth + "px";

      // Create header with title and toggle span
      const header = document.createElement("div");
      header.style.background = "#f0f0f0";
      header.style.padding = "5px";
      header.style.display = "flex";
      header.style.justifyContent = "space-between";
      header.style.alignItems = "center";

      const title = document.createElement("div");
      title.textContent = "Grading Info";
      title.style.margin = "0";
      title.style.fontSize = "larger";
      title.style.fontWeight = "bold";

      const toggleSpan = document.createElement("span");
      toggleSpan.textContent = "▼";
      toggleSpan.style.cursor = "pointer";
      toggleSpan.style.userSelect = "none";
      toggleSpan.style.padding = "0 5px";

      // Create content div
      const contentDiv = document.createElement("div");
      contentDiv.style.padding = "2px 0px 10px 10px";
      contentDiv.style.display = "none"; // Default to hidden

      // Add found divs to content
      contentDiv.appendChild(includesDiv.cloneNode(true));
      contentDiv.appendChild(gradecoDiv.cloneNode(true));
      contentDiv.appendChild(certidDiv.cloneNode(true));

      // Toggle functionality
      toggleSpan.addEventListener("click", () => {
        if (contentDiv.style.display === "none") {
          contentDiv.style.display = "block";
          toggleSpan.textContent = "▲";
        } else {
          contentDiv.style.display = "none";
          toggleSpan.textContent = "▼";
        }
      });

      // Assemble the container
      header.appendChild(title);
      header.appendChild(toggleSpan);
      gradingInfoContainer.appendChild(header);
      gradingInfoContainer.appendChild(contentDiv);

      // Insert the new container where the first div was
      includesDiv.parentNode.insertBefore(gradingInfoContainer, includesDiv);

      // Hide original divs
      includesDiv.style.display = "none";
      gradecoDiv.style.display = "none";
      certidDiv.style.display = "none";

      console.log("Grading Info div created");
    }
  }

  // Use MutationObserver to wait for elements to be added to the DOM
  function initWithObserver() {
    const observer = new MutationObserver((mutations, obs) => {
      const costBasisInput = safeQuerySelector('input[name="cost-basis"]');
      const submitButton = safeQuerySelector(
        'input[type="submit"][value="Add Item"][class="medium button blue"]'
      );
      const includesDiv = safeQuerySelector("#includes");

      if (costBasisInput && submitButton && includesDiv) {
        console.log("Required elements found, initializing script");

        // Populate from storage
        populateFormFromStorage();

        // Add clear button
        addClearButton();

        // Create grading info div
        createGradingInfoDiv();

        // Watch for form submission
        const form = submitButton.closest("form");
        if (form) {
          form.addEventListener("submit", saveFormValues);
          form.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
              saveFormValues(event);
            }
          });
        }

        // Stop observing once elements are found and setup is complete
        obs.disconnect();
      }
    });

    // Start observing the entire document
    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
    });
  }

  // Initialize
  initWithObserver();
})();
