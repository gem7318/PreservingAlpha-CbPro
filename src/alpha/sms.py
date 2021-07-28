

from typing import List, Optional, Union

from twilio.rest import Client
from twilio.rest import TwilioException
from twilio.rest.api.v2010.account.message import MessageInstance


# TODO: (rename) 'SMS' -> 'Twilio'
class SMS(Client):
    """
    Twilio SMS subclass.
    """
    
    def __init__(
        self, username: str, password: str, _from: str, distro: Optional[List[int]],
    ):
        
        super().__init__(username, password)
        
        self._distro = distro or list()
        self._from = _from
        
    def send(self, msg: str, _to: Optional[Union[List, int]] = None) -> List[MessageInstance]:
        """
        Text `msg` to a distribution.
        """
        if _to:
            _to = _to if isinstance(_to, List) else [_to]
        recipients = _to or self.distro
        if not recipients:
            raise ValueError(
                """
                Recipients must be specified by setting `SMS._distro` or
                providing as the `_to` argument of `SMS.send()`.
                """
            )

        try:
            return [
                self.messages.create(
                    to=recip,
                    body=msg,
                    from_=self._from,
                )
                for recip in recipients
            ]
        except TwilioException as e:
            raise e
    
    @property
    def distro(self) -> List[str]:
        """Reformatted distribution list."""
        return [f"+1{n}" for n in self._distro]
