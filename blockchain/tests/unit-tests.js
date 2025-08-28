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

      // Явно работаем с BigInt
      const currentTime = BigInt(await time.latest());
      const startTime = currentTime + 60n; // 60 секунд в будущем
      const duration = 3600n; // 1 час

      const encodedQuestion = ethers.toUtf8Bytes(question);
      const encodedAnswers = answers.map(a => ethers.toUtf8Bytes(a));

      await voting.createPoll(encodedQuestion, encodedAnswers, false, startTime, duration);

      const poll = await voting.getPollInfo(1);

      console.log("\n--- CREATE POLL TEST ---");
      console.log(`✓ Poll created with ID: 1`);
      console.log(`✓ Question (hex): ${poll.question}`);
      console.log(`✓ Start Time: ${poll.startTime.toString()}`);
      console.log(`✓ End Time: ${poll.endTime.toString()}`);
      console.log(`✓ Multiple Choices: ${poll.multipleChoices}`);
      console.log("------------------------\n");

      const hexQuestion = ethers.hexlify(encodedQuestion);
      expect(poll.question).to.equal(hexQuestion);

      const hexAnswers = encodedAnswers.map(a => ethers.hexlify(a));
      expect(poll.answers).to.deep.equal(hexAnswers);

      expect(poll.startTime).to.equal(startTime);
      expect(poll.endTime).to.equal(startTime + duration); // Оба BigInt
    });

    it("Should reject polls with invalid parameters", async function () {
      const currentTime = BigInt(await time.latest());
      const startTime = currentTime + 60n;
      const duration = 3600n;

      const invalidQuestion = ethers.toUtf8Bytes("A".repeat(257)); // >256 символов
      const invalidAnswersSingle = [ethers.toUtf8Bytes("Yes")];
      const invalidAnswersTooMany = Array(17).fill("A").map(a => ethers.toUtf8Bytes(a));

      // Вопрос слишком длинный
      await expect(
        voting.createPoll(
          invalidQuestion,
          [ethers.toUtf8Bytes("Yes"), ethers.toUtf8Bytes("No")],
          false,
          startTime,
          duration
        )
      ).to.be.revertedWith("Invalid question length");
      console.log("✓ Rejected poll with question length > 256");

      // Только один ответ
      await expect(
        voting.createPoll(
          ethers.toUtf8Bytes("Test"),
          invalidAnswersSingle,
          false,
          startTime,
          duration
        )
      ).to.be.revertedWith("Invalid answers count");
      console.log("✓ Rejected poll with 1 answer");

      // Слишком много ответов
      await expect(
        voting.createPoll(
          ethers.toUtf8Bytes("Test"),
          invalidAnswersTooMany,
          false,
          startTime,
          duration
        )
      ).to.be.revertedWith("Invalid answers count");
      console.log("✓ Rejected poll with >16 answers");

      // Время начала в прошлом
      await expect(
        voting.createPoll(
          ethers.toUtf8Bytes("Test"),
          [ethers.toUtf8Bytes("Yes"), ethers.toUtf8Bytes("No")],
          false,
          startTime - 120n,
          duration
        )
      ).to.be.revertedWith("Start time must be future");
      console.log("✓ Rejected poll with start time in past");
    });
  });

  describe("vote()", function () {
    beforeEach(async function () {
      const currentTime = BigInt(await time.latest());
      const startTime = currentTime + 60n;

      await voting.createPoll(
        ethers.toUtf8Bytes("Test"),
        ["Yes", "No"].map(a => ethers.toUtf8Bytes(a)),
        false,
        startTime,
        3600n
      );

      await time.increase(60); // Увеличиваем время на 60 секунд (number допустимо, но можно и 60n)
    });

    it("Should allow valid voting", async function () {
      const [, user1] = await ethers.getSigners();
      await voting.connect(user1).vote(1, [0]);

      const results = await voting.getResults(1);

      console.log("\n--- VOTING TEST ---");
      console.log(`✓ User1 voted for answer 0`);
      console.log(`✓ Votes for 'Yes': ${results[0].toString()}`);
      console.log("------------------\n");

      expect(results[0]).to.equal(1n); // Явно сравниваем с BigInt
    });

    it("Should reject invalid votes", async function () {
      const [, user1] = await ethers.getSigners();

      const futureStartTime = BigInt(await time.latest()) + 60n;
      await voting.createPoll(
        ethers.toUtf8Bytes("Future Poll"),
        ["A", "B"].map(a => ethers.toUtf8Bytes(a)),
        false,
        futureStartTime,
        3600n
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
      const currentTime = BigInt(await time.latest());
      const startTime = currentTime + 60n;

      await voting.createPoll(
        ethers.toUtf8Bytes("Test"),
        ["Yes", "No"].map(a => ethers.toUtf8Bytes(a)),
        false,
        startTime,
        3600n
      );

      await voting.cancelPoll(1);
      const poll = await voting.getPollInfo(1);

      console.log("\n--- CANCEL POLL TEST ---");
      console.log(`✓ Poll ID 1 canceled: ${poll.canceled}`);
      console.log("------------------------\n");

      expect(poll.canceled).to.be.true;
    });

    it("Should reject cancellation after poll starts", async function () {
      const currentTime = BigInt(await time.latest());
      const startTime = currentTime + 60n;

      await voting.createPoll(
        ethers.toUtf8Bytes("Test"),
        ["Yes", "No"].map(a => ethers.toUtf8Bytes(a)),
        false,
        startTime,
        3600n
      );

      await time.increase(60);
      await expect(voting.cancelPoll(1)).to.be.revertedWith("Already started");
      console.log("✓ Rejected cancellation after poll starts");
    });
  });

  describe("updatePollSchedule()", function () {
    it("Should update schedule before poll starts", async function () {
      const currentTime = BigInt(await time.latest());
      const startTime = currentTime + 60n;

      await voting.createPoll(
        ethers.toUtf8Bytes("Test"),
        ["Yes", "No"].map(a => ethers.toUtf8Bytes(a)),
        false,
        startTime,
        3600n
      );

      const newStartTime = startTime + 120n;
      const newDuration = 7200n;

      await voting.updatePollSchedule(1, newStartTime, newDuration);
      const poll = await voting.getPollInfo(1);

      console.log("\n--- UPDATE SCHEDULE TEST ---");
      console.log(`✓ New start time: ${poll.startTime.toString()}`);
      console.log(`✓ New end time: ${poll.endTime.toString()}`);
      console.log("---------------------------\n");

      expect(poll.startTime).to.equal(newStartTime);
      expect(poll.endTime).to.equal(newStartTime + newDuration);
    });

    it("Should reject schedule update after poll starts", async function () {
      const currentTime = BigInt(await time.latest());
      const startTime = currentTime + 60n;

      await voting.createPoll(
        ethers.toUtf8Bytes("Test"),
        ["Yes", "No"].map(a => ethers.toUtf8Bytes(a)),
        false,
        startTime,
        3600n
      );

      await time.increase(60);
      await expect(
        voting.updatePollSchedule(1, startTime + 120n, 7200n)
      ).to.be.revertedWith("Already started");
      console.log("✓ Rejected schedule update after poll starts");
    });
  });
});