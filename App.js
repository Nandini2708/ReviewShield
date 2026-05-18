// Smooth Scroll Navigation
document.querySelectorAll(".navbar li").forEach(item => {
    item.addEventListener("click", () => {
        alert(item.innerText + " section clicked");
    });
});
// Review Form Validation
const submitBtn = document.querySelector(".submit-review");

submitBtn.addEventListener("click", () => {

    const name = document.querySelector('.A input[type="text"]').value;

    const email = document.querySelector('.B input[type="text"]').value;

    const review = document.querySelectorAll('.B input[type="text"]')[1].value;

    const rating = document.querySelector('input[name="rating"]:checked');

    // Validation
    if(name === "" || email === "" || review === "") {
        alert("Please fill all fields");
        return;
    }

    if(!rating) {
        alert("Please select a rating");
        return;
    }

    // Email Validation
    if(!email.includes("@")) {
        alert("Enter valid email");
        return;
    }

    // Fake Spam Detection
    const spamWords = ["fake", "spam", "bad", "worst"];

    let isSpam = spamWords.some(word =>
        review.toLowerCase().includes(word)
    );

    if(isSpam) {
        alert("Spam review detected!");
        return;
    }

    // Success Message
    alert("Review Submitted Successfully!");

});
// Button Hover Animation
const buttons = document.querySelectorAll("button");

buttons.forEach(button => {

    button.addEventListener("mouseover", () => {
        button.style.transform = "scale(1.05)";
        button.style.transition = "0.3s";
    });

    button.addEventListener("mouseout", () => {
        button.style.transform = "scale(1)";
    });

});
// Scroll Animation
window.addEventListener("scroll", () => {

    const sections = document.querySelectorAll(
        ".request, .spam, .analytics"
    );

    sections.forEach(section => {

        const position = section.getBoundingClientRect().top;

        if(position < window.innerHeight - 100) {
            section.style.opacity = "1";
            section.style.transform = "translateY(0)";
            section.style.transition = "0.6s";
        }

    });

});
// Initial Hidden State
document.querySelectorAll(".request, .spam, .analytics")
.forEach(section => {

    section.style.opacity = "0";
    section.style.transform = "translateY(50px)";

});
// Learn More Button
const learnBtn = document.querySelector(".learn-btn");

learnBtn.addEventListener("click", () => {

    alert("Welcome to ReviewShield AI Review System!");

});
// Submit Review Button
const submitReviewBtn = document.querySelector(".submit-btn");

submitReviewBtn.addEventListener("click", () => {

    window.scrollTo({
        top: document.querySelector(".experience").offsetTop,
        behavior: "smooth"
    });

});