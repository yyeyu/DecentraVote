// "npx hardhat test" - to test the contract

const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Voting Contract", function () {
  let Voting;
  let voting;
  let owner, user1, user2;

  beforeEach(async function () {
    Voting = await ethers.getContractFactory("Voting");
    voting = await Voting.deploy();
    await voting.waitForDeployment();

    [owner, user1, user2] = await ethers.getSigners();
  });

  describe("createPoll", function () {
    it("Should create a new poll", async function () {
      const question = "What is your favorite color?";
      const answers = ["Red", "Blue", "Green"];
      const multipleChoices = false;
      const duration = 3600;
    
      await voting.createPoll(question, answers, multipleChoices, duration);
    
      const pollInfo = await voting.getPollInfo(0);
      expect(pollInfo.question).to.equal(question);
      expect(pollInfo.answers).to.deep.equal(answers);
      expect(pollInfo.multipleChoices).to.equal(false);
      expect(pollInfo.startTime).to.be.a('bigint');
      expect(pollInfo.startTime > 0n).to.be.true;
      expect(pollInfo.endTime).to.equal(pollInfo.startTime + BigInt(duration));
    });

    it("Should revert if question is empty", async function () {
      await expect(
        voting.createPoll("", ["Red", "Blue"], false, 3600)
      ).to.be.revertedWith("Invalid question length");
    });

    it("Should revert if question is too long", async function () {
      const longQuestion = "a".repeat(257);
      await expect(
        voting.createPoll(longQuestion, ["Red", "Blue"], false, 3600)
      ).to.be.revertedWith("Invalid question length");
    });

    it("Should revert if less than 2 answers", async function () {
      await expect(
        voting.createPoll("What?", ["Red"], false, 3600)
      ).to.be.revertedWith("Invalid number of answers");
    });

    it("Should revert if too many answers", async function () {
      const manyAnswers = Array(81).fill("Answer");
      await expect(
        voting.createPoll("What?", manyAnswers, false, 3600)
      ).to.be.revertedWith("Invalid number of answers");
    });

    it("Should revert if answer is empty", async function () {
      await expect(
        voting.createPoll("What?", ["Red", ""], false, 3600)
      ).to.be.revertedWith("Invalid answer length");
    });

    it("Should revert if answer is too long", async function () {
      const longAnswer = "a".repeat(101);
      await expect(
        voting.createPoll("What?", ["Red", longAnswer], false, 3600)
      ).to.be.revertedWith("Invalid answer length");
    });

    it("Should revert if duration is zero", async function () {
      await expect(
        voting.createPoll("What?", ["Red", "Blue"], false, 0)
      ).to.be.revertedWith("Duration must be > 0");
    });
  });

  describe("vote", function () {
    beforeEach(async function () {
      const answers = ["Red", "Blue", "Green"];
      await voting.createPoll("Test", answers, false, 3600);
    });

    it("Should allow voting in an active poll", async function () {
      await voting.connect(user1).vote(0, [0]);
      const results = await voting.getResults(0);
      expect(results[0]).to.equal(1);
      expect(results[1]).to.equal(0);
      expect(results[2]).to.equal(0);
    });

    it("Should allow multiple choices in multiple choice poll", async function () {
      const answers = ["Red", "Blue", "Green"];
      await voting.createPoll("Test Multiple", answers, true, 3600);
      
      await voting.connect(user1).vote(1, [0, 1]);
      const results = await voting.getResults(1);
      expect(results[0]).to.equal(1);
      expect(results[1]).to.equal(1);
      expect(results[2]).to.equal(0);
    });

    it("Should revert if poll does not exist", async function () {
      await expect(voting.vote(999, [0])).to.be.revertedWith("Poll does not exist");
    });

    it("Should revert if already voted", async function () {
      await voting.connect(user1).vote(0, [0]);
      await expect(voting.connect(user1).vote(0, [1])).to.be.revertedWith("Already voted");
    });

    it("Should revert if invalid answer ID is provided", async function () {
      await expect(voting.connect(user1).vote(0, [3])).to.be.revertedWith("Invalid answer ID");
    });

    it("Should revert if multiple choices are made in single-choice poll", async function () {
      await expect(voting.connect(user1).vote(0, [0, 1])).to.be.revertedWith("Only one option allowed");
    });
  });

  describe("getResults", function () {
    it("Should return correct results", async function () {
      const answers = ["Red", "Blue", "Green"];
      await voting.createPoll("Test", answers, false, 3600);

      await voting.connect(user1).vote(0, [0]);
      await voting.connect(user2).vote(0, [1]);

      const results = await voting.getResults(0);
      expect(results[0]).to.equal(1);
      expect(results[1]).to.equal(1);
      expect(results[2]).to.equal(0);
    });
  });

  describe("getActivePolls", function () {
    it("Should return only active polls", async function () {
      const answers = ["Red", "Blue"];
      
      // Создаем первый опрос
      await voting.createPoll("Test 1", answers, false, 3600);
      
      // Ждем 1 секунду перед созданием второго опроса
      await ethers.provider.send("evm_increaseTime", [1]);
      await ethers.provider.send("evm_mine", []);
      
      // Создаем второй опрос
      await voting.createPoll("Test 2", answers, false, 3600);
      
      // Проверяем, что оба опроса активны
      let activePolls = await voting.getActivePolls();
      expect(activePolls.length).to.equal(2);
      
      // Ждем окончания первого опроса
      await ethers.provider.send("evm_increaseTime", [3600]);
      await ethers.provider.send("evm_mine", []);
      
      // Проверяем, что остался только второй опрос
      activePolls = await voting.getActivePolls();
      expect(activePolls.length).to.equal(1);
      expect(activePolls[0]).to.equal(1);
    });
  });

  describe("getUserVotes", function () {
    it("Should return user's votes", async function () {
      const answers = ["Red", "Blue", "Green"];
      await voting.createPoll("Test", answers, true, 3600);

      await voting.connect(user1).vote(0, [0, 1]);
      const userVotes = await voting.getUserVotes(0, user1.address);
      expect(userVotes).to.deep.equal([0, 1]);
    });

    it("Should return empty array if user hasn't voted", async function () {
      const answers = ["Red", "Blue"];
      await voting.createPoll("Test", answers, false, 3600);

      const userVotes = await voting.getUserVotes(0, user1.address);
      expect(userVotes).to.deep.equal([]);
    });
  });
});