pragma solidity >=0.7.0 <0.9.0;

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
        require(polls[_pollID].endTime >= block.timestamp, "Poll has ended");
        require(polls[_pollID].startTime <= block.timestamp, "Poll not started");
        _;
    }

    function createPoll (
        string calldata _question,
        string[] calldata _answers,
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
}