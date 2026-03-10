from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm.types import String
from restalchemy.storage.sql.orm import SQLStorableMixin


class Model(models.Model, SQLStorableMixin):
    __tablename__ = "model"

    name = properties.property(String())


class SecondModel(models.Model, SQLStorableMixin):
    __tablename__ = "second_model"
    __engine_name__ = "second"

    name = properties.property(String())



