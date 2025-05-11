const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("Voting Functional Tests", function () {
    let voting, owner, user1, user2;

    beforeEach(async function () {
        [owner, user1, user2] = await ethers.getSigners();
        const Voting = await ethers.getContractFactory("Voting");
        voting = await Voting.deploy();
        await voting.waitForDeployment();
    });

    it("Should handle multiple users and choices", async function () {
        const startTime = (await time.latest()) + 60;
        await voting.createPoll(
            ethers.toUtf8Bytes("Test"),
            ["A", "B", "C"].map(a => ethers.toUtf8Bytes(a)),
            true,
            startTime,
            3600
        );

        await time.increase(60);

        await voting.connect(user1).vote(1, [0, 2]);
        await voting.connect(user2).vote(1, [1]);

        const results = await voting.getResults(1);
        console.log("\n--- MULTI-USER VOTING TEST ---");
        console.log(`✓ User1 votes: 0 and 2`);
        console.log(`✓ User2 votes: 1`);
        console.log(`✓ Results: A(${results[0]}), B(${results[1]}), C(${results[2]})`);
        console.log("--------------------------------\n");
        
        expect(results[0]).to.equal(1);
        expect(results[1]).to.equal(1);
        expect(results[2]).to.equal(1);
    });

    it("Should handle edge cases for multiple choices", async function () {
        const startTime = (await time.latest()) + 60;
        await voting.createPoll(
            ethers.toUtf8Bytes("Test"),
            ["A", "B"].map(a => ethers.toUtf8Bytes(a)),
            true,
            startTime,
            3600
        );

        await time.increase(60);

        await voting.connect(user1).vote(1, [0, 1]);
        const results = await voting.getResults(1);
        console.log("\n--- MULTIPLE CHOICE EDGE CASE ---");
        console.log(`✓ User1 voted for all answers`);
        console.log(`✓ Results: A(${results[0]}), B(${results[1]})`);
        console.log("----------------------------------\n");
        expect(results[0]).to.equal(1);
        expect(results[1]).to.equal(1);
    });
});