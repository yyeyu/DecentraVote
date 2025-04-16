// SPDX-License-Identifier: MIT
pragma solidity >=0.7.0 < 0.9.0;

contract Voting {

    struct Poll {
        uint pollID;
        address creator;
        uint startTime;
        uint endTime;
        string question;
        string[] answers;
        bool multipleChoices;
        mapping(uint => uint) votes;
        mapping(address => uint[]) userVotes;
    }

    mapping(uint => Poll) public polls;
    uint public nextPollID;

    event PollCreated(uint pollID, address creator, string question);
    event Voted(address voter, uint pollID, uint[] answerIDs);

    modifier pollActive(uint _pollID) {
        Poll storage poll = polls[_pollID];
        require(poll.startTime != 0, "Poll does not exist");
        require(poll.endTime >= block.timestamp, "Poll has ended");
        require(poll.startTime <= block.timestamp, "Poll not started");
        _;
    }

    modifier onlyCreator(uint _pollID) {
        require(msg.sender == polls[_pollID].creator, "Not creator");
        _;
    }

    function createPoll (
        string calldata _question,
        string[] memory _answers,
        bool _multipleChoices,
        uint _duration
    ) public {
        require(bytes(_question).length > 0, "Question cannot be empty");
        require(_answers.length > 1, "Need at least 2 answers");
        require(_duration > 0, "Duration must be > 0");

        Poll storage newPoll = polls[nextPollID];

        newPoll.pollID = nextPollID;
        newPoll.creator = msg.sender;
        newPoll.startTime = block.timestamp;
        newPoll.endTime = block.timestamp + _duration;
        newPoll.question = _question;
        newPoll.answers = _answers;
        newPoll.multipleChoices = _multipleChoices;

        nextPollID++;
        emit PollCreated(newPoll.pollID, msg.sender, _question);
    }

    function vote(uint _pollID, uint[] memory _answerIDs) public pollActive(_pollID) {
        Poll storage poll = polls[_pollID];
        require(poll.userVotes[msg.sender].length == 0, "Already voted");

        if (!poll.multipleChoices) {
            require(_answerIDs.length == 1, "Only one option allowed");
        }
        
        for (uint i = 0; i < _answerIDs.length; i++) {
            require(_answerIDs[i] < poll.answers.length, "Invalid answer ID");
        }

        poll.userVotes[msg.sender] = _answerIDs;
        for (uint i = 0; i < _answerIDs.length; i++) {
            poll.votes[_answerIDs[i]]++;
        }
        
        emit Voted(msg.sender, _pollID, _answerIDs);
    }

    function getResults(uint _pollID) public view returns (uint[] memory) {
        Poll storage poll = polls[_pollID];
        uint[] memory results = new uint[](poll.answers.length);
        for (uint i = 0; i < poll.answers.length; i++) {
            results[i] = poll.votes[i];
        }
        return results;
    }

    function getAllPolls() public view returns (uint[] memory) {
        uint[] memory pollIDs = new uint[](nextPollID);
        for (uint i = 0; i < nextPollID; i++) {
            pollIDs[i] = i;
        }
        return pollIDs;
    }

    function getAnswers(uint _pollID) external view returns (string[] memory) {
        Poll storage poll = polls[_pollID];
        require(polls[_pollID].startTime != 0, "Poll does not exist");
        return poll.answers;
    }
}