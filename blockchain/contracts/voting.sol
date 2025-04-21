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
    uint public constant MAX_ANSWERS = 80;
    uint public constant MAX_QUESTION_LENGTH = 256;
    uint public constant MAX_ANSWER_LENGTH = 100;

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
        require(bytes(_question).length > 0 && bytes(_question).length <= MAX_QUESTION_LENGTH, "Invalid question length");
        require(_answers.length > 1 && _answers.length <= MAX_ANSWERS, "Invalid number of answers");
        require(_duration > 0, "Duration must be > 0");

        for (uint i = 0; i < _answers.length; i++) {
            require(bytes(_answers[i]).length > 0 && bytes(_answers[i]).length <= MAX_ANSWER_LENGTH, "Invalid answer length");
        }

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

    function getPollInfo(uint _pollID) public view returns (
        address creator,
        uint startTime,
        uint endTime,
        string memory question,
        string[] memory answers,
        bool multipleChoices
    ) {
        Poll storage poll = polls[_pollID];
        require(poll.startTime != 0, "Poll does not exist");
        
        return (
            poll.creator,
            poll.startTime,
            poll.endTime,
            poll.question,
            poll.answers,
            poll.multipleChoices
        );
    }

    function getResults(uint _pollID) public view returns (uint[] memory) {
        Poll storage poll = polls[_pollID];
        uint[] memory results = new uint[](poll.answers.length);
        for (uint i = 0; i < poll.answers.length; i++) {
            results[i] = poll.votes[i];
        }
        return results;
    }

    function getActivePolls() public view returns (uint[] memory) {
        uint count = 0;
        for (uint i = 0; i < nextPollID; i++) {
            if (polls[i].endTime >= block.timestamp) {
                count++;
            }
        }
        
        uint[] memory activePolls = new uint[](count);
        uint index = 0;
        for (uint i = 0; i < nextPollID; i++) {
            if (polls[i].endTime >= block.timestamp) {
                activePolls[index] = i;
                index++;
            }
        }
        return activePolls;
    }

    function getUserVotes(uint _pollID, address _user) public view returns (uint[] memory) {
        return polls[_pollID].userVotes[_user];
    }
}