document.addEventListener("DOMContentLoaded", () => {
  fetch("/api/ebay-orders")
    .then((response) => response.json())
    .then((orders) => {
      displayOrders(orders);
    })
    .catch((error) => console.error("Error fetching orders:", error));

  function displayOrders(orders) {
    const table = document.createElement("table");
    table.id = "ebay-orders-table";
    const thead = document.createElement("thead");
    const tbody = document.createElement("tbody");

    // Table headers
    thead.innerHTML = `
            <tr>
                <th>#</th>
                <th>Order ID</th>
                <th>Payment Date</th>
                <th>Items</th>
                <th>Item Cost</th>
                <th>Delivery Cost</th>
                <th>Marketplace Fee</th>
                <th>Actions</th>
            </tr>
        `;
    table.appendChild(thead);

    let i = 0;
    orders.forEach((order) => {
      const row = document.createElement("tr");
      const numCell = document.createElement("td");
      numCell.textContent = ++i;
      row.appendChild(numCell);

      // Order ID
      const orderId = order.orderId || "";
      const orderIdCell = document.createElement("td");
      orderIdCell.textContent = orderId;
      row.appendChild(orderIdCell);

      // Payment Date
      let paymentDate = "";
      if (
        order.paymentSummary &&
        order.paymentSummary.payments &&
        order.paymentSummary.payments.length > 0
      ) {
        paymentDate = new Date(order.paymentSummary.payments[0].paymentDate);
        paymentDate = `${paymentDate.getMonth() + 1}/${paymentDate.getDate()}/${paymentDate.getFullYear()} ${paymentDate.getHours()}:${paymentDate.getMinutes()}:${paymentDate.getSeconds()}`;
      }
      const paymentDateCell = document.createElement("td");
      paymentDateCell.textContent = paymentDate;
      row.appendChild(paymentDateCell);

      // Line Items
      const lineItems = order.lineItems || [];
      const itemTitles = lineItems.map((item) => item.title).join("\n");
      const itemsCell = document.createElement("td");
      itemsCell.textContent = itemTitles;
      row.appendChild(itemsCell);

      // Item Cost
      const itemCost = lineItems.reduce(
        (sum, item) => sum + parseFloat(item.lineItemCost.value),
        0,
      );
      const itemCostCell = document.createElement("td");
      itemCostCell.textContent = itemCost.toFixed(2);
      row.appendChild(itemCostCell);

      // Delivery Cost
      let deliveryCostValue = lineItems.reduce((sum, item) => {
        if (item.deliveryCost && item.deliveryCost.shippingCost) {
          return sum + parseFloat(item.deliveryCost.shippingCost.value);
        } else {
          return sum;
        }
      }, 0);
      const deliveryCostCell = document.createElement("td");
      deliveryCostCell.textContent = deliveryCostValue.toFixed(2);
      row.appendChild(deliveryCostCell);

      // Marketplace Fee
      const marketplaceFee = order.totalMarketplaceFee
        ? parseFloat(order.totalMarketplaceFee.value)
        : 0;
      const marketplaceFeeCell = document.createElement("td");
      marketplaceFeeCell.textContent = marketplaceFee.toFixed(2);
      row.appendChild(marketplaceFeeCell);

      // Add to Sheets Link
      const addToSheetsCell = document.createElement("td");
      const addToSheetsLink = document.createElement("a");
      addToSheetsLink.href = "#";
      addToSheetsLink.textContent = "Add to Sheets";
      addToSheetsLink.addEventListener("click", (event) => {
        event.preventDefault();
        addToSheets(order);
      });
      addToSheetsCell.appendChild(addToSheetsLink);
      row.appendChild(addToSheetsCell);

      tbody.appendChild(row);
    });

    table.appendChild(tbody);
    const container = document.getElementById("ebay-orders-container");
    container.appendChild(table);
  }

  async function addToSheets(order) {
    //     // Check if sale_date is empty before adding to sheets
    //     if (
    //         order.paymentSummary &&
    //         order.paymentSummary.payments &&
    //         order.paymentSummary.payments.length > 0 &&
    //         order.paymentSummary.payments[0].paymentDate
    //     ) {
    //         alert("Sale date is not empty. Not adding to sheets.");
    //         return;
    //     }

    try {
      const response = await fetch("/api/add-to-sheets", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(order),
      });

      if (response.ok) {
        alert("Order added to Google Sheets successfully!");
      } else {
        const errorData = await response.json();
        alert(`Failed to add order to Google Sheets: ${errorData.detail}`);
      }
    } catch (error) {
      console.error("Error adding to Google Sheets:", error);
      alert("Error adding order to Google Sheets.");
    }
  }
});
