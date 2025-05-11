const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");
const { expect } = require("chai");

describe("Voting Load Tests", function () {
    let voting, owner, users;

    beforeEach(async function () {
        [owner, ...users] = await ethers.getSigners();
        const Voting = await ethers.getContractFactory("Voting");
        voting = await Voting.deploy();
        await voting.waitForDeployment();
    });

    it("Should handle 50 polls with 10 votes each", async function () {
        const startTime = (await time.latest()) + 60;
        const duration = 3600;

        console.time("Create 50 polls");
        for (let i = 0; i < 50; i++) {
            await voting.createPoll(
                ethers.toUtf8Bytes(`Poll ${i}`),
                ["Yes", "No"].map(answer => ethers.toUtf8Bytes(answer)),
                false,
                startTime,
                duration
            );
        }
        console.timeEnd("Create 50 polls");

        await time.increaseTo(startTime);

        console.time("Vote 10 times per poll");
        for (let i = 1; i <= 50; i++) {
            for (let j = 0; j < 10; j++) {
                await voting.connect(users[j]).vote(i, [0]);
            }
        }
        console.timeEnd("Vote 10 times per poll");

        for (let i = 1; i <= 50; i++) {
            const results = await voting.getResults(i);
            expect(results[0]).to.equal(10);
        }
    });
});