// ==UserScript==
// @name         SportsCardsPro - Add Card Overlay to Checklist
// @namespace    http://tampermonkey.net/
// @version      1.5
// @author       jessedp <jessedp@gmail.com>
// @description  Add button to open overlay on SportsCardsPro (Improved)
// @match        https://www.sportscardspro.com/console/*
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  function debounce(func, wait, immediate) {
    let timeout;
    return function () {
      const context = this,
        args = arguments;
      const later = function () {
        timeout = null;
        if (!immediate) func.apply(context, args);
      };
      const callNow = immediate && !timeout;
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
      if (callNow) func.apply(context, args);
    };
  }

  function processLinks() {
    const collectionItems = document.querySelectorAll("li.add_to.collection");
    let i = 0;
    collectionItems.forEach((item) => {
      const link = item.querySelector('a[href*="add-to-collection=1"]');
      if (link && !item.classList.contains("processed-by-tampermonkey")) {
        const button = document.createElement("button");
        button.textContent = "add card";
        button.className = "overlay-button";
        button.style.backgroundColor = "#4CAF50";
        button.style.color = "white";
        button.style.padding = "4px 8px";
        button.style.border = "none";
        button.style.borderRadius = "4px";
        button.style.cursor = "pointer";
        button.style.marginLeft = "8px";

        button.addEventListener("click", function (event) {
          event.preventDefault();
          const href = link.getAttribute("href");

          const overlay = document.createElement("div");
          overlay.style.position = "fixed";
          overlay.style.top = "0";
          overlay.style.left = "0";
          overlay.style.width = "100%";
          overlay.style.height = "100%";
          overlay.style.backgroundColor = "rgba(0,0,0,0.5)";
          overlay.style.display = "flex";
          overlay.style.justifyContent = "center";
          overlay.style.alignItems = "center";
          overlay.style.zIndex = "1000";

          const iframe = document.createElement("iframe");
          iframe.style.backgroundColor = "white";
          iframe.style.border = "solid";
          iframe.style.width = "40vw";
          iframe.style.height = "100vh";
          iframe.src = href;

          const closeButton = document.createElement("button");
          closeButton.textContent = "Close";
          closeButton.style.marginTop = "10px";
          closeButton.style.backgroundColor = "#f44336";
          closeButton.style.color = "white";
          closeButton.style.padding = "8px 16px";
          closeButton.style.border = "none";
          closeButton.style.borderRadius = "4px";
          closeButton.style.cursor = "pointer";

          closeButton.addEventListener("click", function () {
            document.body.removeChild(overlay);
          });

          const container = document.createElement("div");
          container.appendChild(iframe);
          container.appendChild(closeButton);
          overlay.appendChild(container);
          document.body.appendChild(overlay);

          iframe.onload = function () {
            const header = iframe.contentDocument.querySelector("div.top_bar");
            header.style.display = "none";
            const login = iframe.contentDocument.querySelector("div.login");
            login.style.display = "none";
            const submitButton = iframe.contentDocument.querySelector(
              'input[type="submit"][value="Add Item"].medium.button.blue'
            );
            if (submitButton) {
              submitButton.addEventListener("click", function () {
                // Wait for page load or 2 seconds, then close overlay and reload
                let pageLoaded = false;

                iframe.onload = function () {
                  setTimeout(function () {
                    if (!pageLoaded) {
                      document.body.removeChild(overlay);
                      reloadPageWithoutQueryParams();
                    }
                  }, 100);
                };
              });
            }
          };
        });

        const listItem = document.createElement("li");
        listItem.appendChild(button);
        item.prepend(listItem);
        item.classList.add("processed-by-tampermonkey");
      }
    });
  }

  function reloadPageWithoutQueryParams() {
    const newUrl = window.location.origin + window.location.pathname; // Origin and pathname only
    window.location.href = newUrl;
  }

  const targetNode = document.querySelector(".console-list");
  if (targetNode) {
    const observer = new MutationObserver(
      debounce(function (mutations) {
        mutations.forEach(function (mutation) {
          if (mutation.addedNodes && mutation.addedNodes.length > 0) {
            processLinks();
          }
        });
      }, 250)
    );

    observer.observe(targetNode, { childList: true, subtree: true });
  }

  // Save original XMLHttpRequest
  const originalXHR = window.XMLHttpRequest;

  // Create a proxy for XMLHttpRequest
  class XHRInterceptor extends originalXHR {
    constructor() {
      super();

      this.addEventListener("readystatechange", () => {
        if (this.readyState === 4) {
          processLinks();
          setTimeout(processLinks, 250);
          console.log("Intercepted request to:", this.responseURL);
        }
      });
    }
  }

  // Replace XMLHttpRequest with the proxy
  window.XMLHttpRequest = XHRInterceptor;
})();
