// SPDX-License-Identifier: MIT
pragma solidity >=0.8.0 <0.9.0;

contract Voting {

    struct Poll {
        uint id;
        address creator;
        uint startTime;
        uint endTime;
        bytes question;
        bytes[] answers;
        bool multipleChoices;
        bool canceled;
        mapping(uint => uint) votes;
        mapping(address => uint[]) userVotes;
    }

    mapping(uint => Poll) private _polls;
    uint public nextPollID;
    
    
    uint public maxAnswers = 16;
    uint public maxQuestionLength = 256;
    uint public maxAnswerLength = 128;
    uint public minDuration = 1 minutes;
    uint public maxDuration = 365 days;

    event PollCreated(uint indexed id, address creator, bytes question);
    event PollCanceled(uint indexed id);
    event PollEdited(uint indexed id);
    event Voted(address indexed voter, uint indexed pollID, uint[] answerIDs, uint timestamp);
    event ScheduleUpdated(uint indexed pollID, uint newStartTime);

    modifier onlyCreator(uint _pollID) {
        require(msg.sender == _polls[_pollID].creator, "Not creator");
        _;
    }

    modifier pollActive(uint _pollID) {
        Poll storage poll = _polls[_pollID];
        require(poll.startTime != 0, "Poll does not exist");
        require(block.timestamp >= poll.startTime, "Poll not started");
        require(block.timestamp <= poll.endTime, "Poll ended");
        require(!poll.canceled, "Poll canceled");
        _;
    }

    modifier pollExists(uint _pollID) {
        require(_polls[_pollID].id != 0, "Poll does not exist");
        _;
    }

    modifier validSchedule(uint _startTime, uint _duration) {
        require(_startTime > block.timestamp, "Start time must be future");
        require(_duration >= minDuration, "Duration too short");
        require(_duration <= maxDuration, "Duration too long");
        _;
    }

    constructor() {
        nextPollID = 1;
    }

    function createPoll(
        bytes calldata _question,
        bytes[] calldata _answers,
        bool _multipleChoices,
        uint _startTime,
        uint _duration
    ) 
        external 
        validSchedule(_startTime, _duration)
    {
        require(bytes(_question).length <= maxQuestionLength, "Invalid question length");
        require(_answers.length > 1 && _answers.length <= maxAnswers, "Invalid answers count");
        
        for (uint i = 0; i < _answers.length; i++) {
            require(bytes(_answers[i]).length <= maxAnswerLength, "Invalid answer length");
        }

        uint pollID = nextPollID++;
        Poll storage newPoll = _polls[pollID];
        newPoll.id = pollID;
        newPoll.creator = msg.sender;
        newPoll.startTime = _startTime;
        newPoll.endTime = _startTime + _duration;
        newPoll.question = _question;
        newPoll.answers = _answers;
        newPoll.multipleChoices = _multipleChoices;

        emit PollCreated(pollID, msg.sender, _question);
    }

    function vote(uint _pollID, uint[] calldata _answerIDs) 
        external 
        pollActive(_pollID)
    {
        Poll storage poll = _polls[_pollID];
        require(poll.userVotes[msg.sender].length == 0, "Already voted");
        require(_answerIDs.length > 0, "No answers selected");
        
        if (!poll.multipleChoices) {
            require(_answerIDs.length == 1, "Only single choice allowed");
        }

        for (uint i = 0; i < _answerIDs.length; i++) {
            require(_answerIDs[i] < poll.answers.length, "Invalid answer ID");
        }

        poll.userVotes[msg.sender] = _answerIDs;
        for (uint i = 0; i < _answerIDs.length; i++) {
            poll.votes[_answerIDs[i]]++;
        }
        
        emit Voted(msg.sender, _pollID, _answerIDs, block.timestamp);
    }

    function cancelPoll(uint _pollID) 
        external 
        onlyCreator(_pollID) 
        pollExists(_pollID)
    {
        Poll storage poll = _polls[_pollID];
        require(block.timestamp < poll.startTime, "Already started");
        poll.canceled = true;
        emit PollCanceled(_pollID);
    }

    function updatePollSchedule(
        uint _pollID,
        uint _newStartTime,
        uint _newDuration
    ) 
        external 
        onlyCreator(_pollID)
        validSchedule(_newStartTime, _newDuration)
        pollExists(_pollID)
    {
        Poll storage poll = _polls[_pollID];
        require(block.timestamp < poll.startTime, "Already started");
        
        poll.startTime = _newStartTime;
        poll.endTime = _newStartTime + _newDuration;
        emit ScheduleUpdated(_pollID, _newStartTime);
    }

    function getPollInfo(uint _pollID) 
        external 
        view 
        pollExists(_pollID) 
        returns (
            address creator,
            uint startTime,
            uint endTime,
            bytes memory question,
            bytes[] memory answers,
            bool multipleChoices,
            bool canceled
        ) 
    {
        Poll storage poll = _polls[_pollID];
        return (
            poll.creator,
            poll.startTime,
            poll.endTime,
            poll.question,
            poll.answers,
            poll.multipleChoices,
            poll.canceled
        );
    }

    function getResults(uint _pollID) 
        external 
        view 
        pollExists(_pollID) 
        returns (uint[] memory) 
    {
        Poll storage poll = _polls[_pollID];
        uint[] memory results = new uint[](poll.answers.length);
        for (uint i = 0; i < poll.answers.length; i++) {
            results[i] = poll.votes[i];
        }
        return results;
    }

    function getUserVotes(uint _pollID, address _user) 
        external 
        view 
        pollExists(_pollID) 
        returns (uint[] memory) 
    {
        return _polls[_pollID].userVotes[_user];
    }
}