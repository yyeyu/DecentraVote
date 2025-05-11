const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("Voting Unit Tests", function () {
    let voting;

    beforeEach(async function () {
        const Voting = await ethers.getContractFactory("Voting");
        voting = await Voting.deploy();
        await voting.waitForDeployment();
    });

    describe("createPoll()", function () {
        it("Should create a valid poll", async function () {
            const question = "Test Question?";
            const answers = ["Yes", "No"];
            const startTime = (await time.latest()) + 60;
            const duration = 3600;
        
            const encodedQuestion = ethers.toUtf8Bytes(question);
            const encodedAnswers = answers.map(answer => ethers.toUtf8Bytes(answer));
        
            await voting.createPoll(encodedQuestion, encodedAnswers, false, startTime, duration);
        
            const poll = await voting.getPollInfo(1);
            console.log("\n--- CREATE POLL TEST ---");
            console.log(`✓ Poll created with ID: 1`);
            console.log(`✓ Question: ${poll.question}`);
            console.log(`✓ Start Time: ${poll.startTime}`);
            console.log(`✓ End Time: ${poll.endTime}`);
            console.log(`✓ Multiple Choices: ${poll.multipleChoices}`);
            console.log("------------------------\n");

            const hexQuestion = ethers.hexlify(encodedQuestion);
            expect(poll.question).to.equal(hexQuestion);
            const hexAnswers = encodedAnswers.map(answer => ethers.hexlify(answer));
            expect(poll.answers).to.deep.equal(hexAnswers);
            expect(poll.startTime).to.equal(startTime);
            expect(poll.endTime).to.equal(startTime + duration);
        });

        it("Should reject polls with invalid parameters", async function () {
            const startTime = (await time.latest()) + 60;
            const duration = 3600;

            const invalidQuestion = ethers.toUtf8Bytes("A".repeat(257));
            const invalidAnswersSingle = [ethers.toUtf8Bytes("Yes")];
            const invalidAnswersTooMany = Array(17).fill("A").map(answer => ethers.toUtf8Bytes(answer));

            await expect(voting.createPoll(
                invalidQuestion, [ethers.toUtf8Bytes("Yes"), ethers.toUtf8Bytes("No")], false, startTime, duration
            )).to.be.revertedWith("Invalid question length");
            console.log("✓ Rejected poll with question length > 256");

            await expect(voting.createPoll(
                ethers.toUtf8Bytes("Test"), invalidAnswersSingle, false, startTime, duration
            )).to.be.revertedWith("Invalid answers count");
            console.log("✓ Rejected poll with 1 answer");

            await expect(voting.createPoll(
                ethers.toUtf8Bytes("Test"), invalidAnswersTooMany, false, startTime, duration
            )).to.be.revertedWith("Invalid answers count");
            console.log("✓ Rejected poll with >16 answers");

            await expect(voting.createPoll(
                ethers.toUtf8Bytes("Test"), [ethers.toUtf8Bytes("Yes"), ethers.toUtf8Bytes("No")], false, startTime - 120, duration
            )).to.be.revertedWith("Start time must be future");
            console.log("✓ Rejected poll with start time in past");
        });
    });

    describe("vote()", function () {
        beforeEach(async function () {
            const startTime = (await time.latest()) + 60;
            await voting.createPoll(
                ethers.toUtf8Bytes("Test"),
                ["Yes", "No"].map(answer => ethers.toUtf8Bytes(answer)),
                false,
                startTime,
                3600
            );

            await time.increase(60);
        });

        it("Should allow valid voting", async function () {
            const [owner, user1] = await ethers.getSigners();
            await voting.connect(user1).vote(1, [0]);
            const results = await voting.getResults(1);
            console.log("\n--- VOTING TEST ---");
            console.log(`✓ User1 voted for answer 0`);
            console.log(`✓ Votes for 'Yes': ${results[0]}`);
            console.log("------------------\n");
            expect(results[0]).to.equal(1);
        });

        it("Should reject invalid votes", async function () {
            const [owner, user1] = await ethers.getSigners();
            const futureStartTime = (await time.latest()) + 60;
            await voting.createPoll(
                ethers.toUtf8Bytes("Future Poll"),
                ["A", "B"].map(answer => ethers.toUtf8Bytes(answer)),
                false,
                futureStartTime,
                3600
            );

            await expect(voting.connect(user1).vote(2, [0])).to.be.revertedWith("Poll not started");
            console.log("✓ Rejected vote before poll starts");

            await expect(voting.connect(user1).vote(1, [2])).to.be.revertedWith("Invalid answer ID");
            console.log("✓ Rejected vote with invalid answer ID");

            await voting.connect(user1).vote(1, [0]);
            await expect(voting.connect(user1).vote(1, [1])).to.be.revertedWith("Already voted");
            console.log("✓ Rejected duplicate vote");

            await time.increase(3601);
            await expect(voting.connect(user1).vote(1, [0])).to.be.revertedWith("Poll ended");
            console.log("✓ Rejected vote after poll ends");
        });
    });

    describe("cancelPoll()", function () {
        it("Should cancel a poll before it starts", async function () {
            const startTime = (await time.latest()) + 60;
            await voting.createPoll(
                ethers.toUtf8Bytes("Test"),
                ["Yes", "No"].map(answer => ethers.toUtf8Bytes(answer)),
                false,
                startTime,
                3600
            );

            await voting.cancelPoll(1);
            const poll = await voting.getPollInfo(1);
            console.log("\n--- CANCEL POLL TEST ---");
            console.log(`✓ Poll ID 1 canceled: ${poll.canceled}`);
            console.log("------------------------\n");
            expect(poll.canceled).to.equal(true);
        });

        it("Should reject cancellation after poll starts", async function () {
            const startTime = (await time.latest()) + 60;
            await voting.createPoll(
                ethers.toUtf8Bytes("Test"),
                ["Yes", "No"].map(answer => ethers.toUtf8Bytes(answer)),
                false,
                startTime,
                3600
            );

            await time.increase(60);
            await expect(voting.cancelPoll(1)).to.be.revertedWith("Already started");
            console.log("✓ Rejected cancellation after poll starts");
        });
    });

    describe("updatePollSchedule()", function () {
        it("Should update schedule before poll starts", async function () {
            const startTime = (await time.latest()) + 60;
            await voting.createPoll(
                ethers.toUtf8Bytes("Test"),
                ["Yes", "No"].map(answer => ethers.toUtf8Bytes(answer)),
                false,
                startTime,
                3600
            );

            const newStartTime = startTime + 120;
            await voting.updatePollSchedule(1, newStartTime, 7200);
            const poll = await voting.getPollInfo(1);
            console.log("\n--- UPDATE SCHEDULE TEST ---");
            console.log(`✓ New start time: ${poll.startTime}`);
            console.log(`✓ New end time: ${poll.endTime}`);
            console.log("---------------------------\n");
            expect(poll.startTime).to.equal(newStartTime);
            expect(poll.endTime).to.equal(newStartTime + 7200);
        });

        it("Should reject schedule update after poll starts", async function () {
            const startTime = (await time.latest()) + 60;
            await voting.createPoll(
                ethers.toUtf8Bytes("Test"),
                ["Yes", "No"].map(answer => ethers.toUtf8Bytes(answer)),
                false,
                startTime,
                3600
            );

            await time.increase(60);
            await expect(voting.updatePollSchedule(1, startTime + 120, 7200)).to.be.revertedWith("Already started");
            console.log("✓ Rejected schedule update after poll starts");
        });
    });
});