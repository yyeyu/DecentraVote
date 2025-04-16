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
    
      const poll = await voting.polls(0);
      expect(poll.question).to.equal(question);
      expect(await voting.getAnswers(0)).to.deep.equal(answers);
      expect(poll.multipleChoices).to.equal(false);
      expect(poll.startTime).to.be.a('bigint');
      expect(poll.startTime > 0n).to.be.true;
      expect(poll.endTime).to.equal(poll.startTime + BigInt(duration));
    });

    it("Should revert if question is empty", async function () {
      await expect(
        voting.createPoll("", ["Red", "Blue"], false, 3600)
      ).to.be.revertedWith("Question cannot be empty");
    });

    it("Should revert if less than 2 answers", async function () {
      await expect(
        voting.createPoll("What?", ["Red"], false, 3600)
      ).to.be.revertedWith("Need at least 2 answers");
    });

    it("Should revert if duration is zero", async function () {
      await expect(
        voting.createPoll("What?", ["Red", "Blue"], false, 0)
      ).to.be.revertedWith("Duration must be > 0");
    });
  });

  describe("vote", function () {
    it("Should allow voting in an active poll", async function () {
      const answers = ["Red", "Blue"];
      await voting.createPoll("Test", answers, false, 3600);

      await voting.connect(user1).vote(0, [0]);
      const results = await voting.getResults(0);
      expect(results[0]).to.equal(1); // Голос за Red
      expect(results[1]).to.equal(0); // Нет голосов за Blue
    });

    it("Should revert if poll does not exist", async function () {
      await expect(voting.vote(999, [0])).to.be.revertedWith("Poll does not exist");
    });

    it("Should revert if already voted", async function () {
      const answers = ["Red", "Blue"];
      await voting.createPoll("Test", answers, false, 3600);

      await voting.connect(user1).vote(0, [0]);
      await expect(voting.connect(user1).vote(0, [1])).to.be.revertedWith("Already voted");
    });

    it("Should revert if invalid answer ID is provided", async function () {
      const answers = ["Red", "Blue"];
      await voting.createPoll("Test", answers, false, 3600);

      await expect(voting.connect(user1).vote(0, [2])).to.be.revertedWith("Invalid answer ID");
    });

    it("Should revert if multiple choices are made in single-choice poll", async function () {
      const answers = ["Red", "Blue"];
      await voting.createPoll("Test", answers, false, 3600);

      await expect(voting.connect(user1).vote(0, [0, 1])).to.be.revertedWith("Only one option allowed");
    });
  });

  describe("getResults", function () {
    it("Should return correct results", async function () {
      const answers = ["Red", "Blue"];
      await voting.createPoll("Test", answers, false, 3600);

      await voting.connect(user1).vote(0, [0]);
      await voting.connect(user2).vote(0, [1]);

      const results = await voting.getResults(0);
      expect(results[0]).to.equal(1); // Голос за Red
      expect(results[1]).to.equal(1); // Голос за Blue
    });
  });

  describe("getAllPolls", function () {
    it("Should return all poll IDs", async function () {
      const answers = ["Red", "Blue"];
      await voting.createPoll("Test 1", answers, false, 3600);
      await voting.createPoll("Test 2", answers, false, 3600);

      const pollIDs = await voting.getAllPolls();
      expect(pollIDs).to.deep.equal([0, 1]);
    });
  });
});