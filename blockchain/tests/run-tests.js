const { execSync } = require("child_process");

function runTests() {
    try {
        console.log("\n--- RUNNING UNIT TESTS ---");
        execSync("npx hardhat test tests/unit-tests.js", { stdio: "inherit" });

        console.log("\n--- RUNNING FUNCTIONAL TESTS ---");
        execSync("npx hardhat test tests/func-tests.js", { stdio: "inherit" });

        console.log("\n--- RUNNING LOAD TESTS ---");
        execSync("npx hardhat test tests/load-tests.js", { stdio: "inherit" });

        console.log("\n--- ALL TESTS COMPLETED ---");
    } catch (error) {
        console.error("❌ Test failed:", error.message);
    }
}

runTests();