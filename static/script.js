const form = document.querySelector("form");

form.addEventListener("submit", async function(event) {
    event.preventDefault();

   const complaint = {
    name: document.getElementById("name").value,
    mobile: document.getElementById("mobile").value,
    category: document.getElementById("category").value,
    location: document.getElementById("location").value,
    description: document.getElementById("description").value
};
    try {
        const response = await fetch("/submit", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(complaint)
        });

        const result = await response.json();

        if (response.ok) {
            alert(
                "Complaint submitted successfully!\n\n" +
                "Complaint ID: " + result.complaint_id
            );

            form.reset();
        } else {
            alert("Failed to submit complaint.");
        }
    } catch (error) {
        alert("Cannot connect to the server. Please try again.");
        console.error(error);
    }
});
// Track complaint status
const trackButton = document.getElementById("track-button");
const complaintIdInput = document.getElementById("track-id");
const trackingResult = document.getElementById("tracking-result");

trackButton.addEventListener("click", async function () {
    const complaintId = complaintIdInput.value.trim();

    if (!complaintId) {
        alert("Please enter your Complaint ID.");
        return;
    }

    try {
        const response = await fetch(`/track/${complaintId}`);
        const result = await response.json();

        if (!response.ok) {
            trackingResult.textContent =
                result.error || "Complaint not found.";
            return;
        }

        trackingResult.innerHTML = `
            <h3>Complaint Details</h3>
            <p><strong>Complaint ID:</strong> ${result.id}</p>
            <p><strong>Category:</strong> ${result.category}</p>
            <p><strong>Location:</strong> ${result.location}</p>
            <p><strong>Status:</strong> ${result.status}</p>
        `;
    } catch (error) {
        console.error("Tracking error:", error);
        trackingResult.textContent =
            "Unable to track complaint. Please try again.";
    }
});